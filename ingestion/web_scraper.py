"""
Web scraper for enriching RSS-ingested articles with full content.

Fetches the actual article body when the RSS feed only provides a short
summary. Uses requests + BeautifulSoup to extract paragraph text.
"""

import json
import logging
import os

import requests
from bs4 import BeautifulSoup

from utils import project_path

logger = logging.getLogger(__name__)

RAW_DIR = project_path("queue", "incoming_raw")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
}

# Articles with summaries shorter than this get enriched via scraping
MIN_SUMMARY_LENGTH = 500


def scrape_article(url: str) -> str:
    """Fetch and extract paragraph text from a URL."""
    try:
        response = requests.get(url, timeout=15, headers=_HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        paragraphs = soup.find_all("p")
        content = " ".join(p.text.strip() for p in paragraphs if p.text.strip())
        return content
    except Exception as e:
        logger.error("Error scraping %s: %s", url, e)
        return ""


def update_raw_files() -> int:
    """Enrich raw articles with thin summaries by scraping the source URL.

    Scrapes articles where summary_raw is empty or shorter than
    MIN_SUMMARY_LENGTH characters. Returns count of enriched articles.
    """
    if not os.path.isdir(RAW_DIR):
        logger.warning("Raw directory does not exist: %s", RAW_DIR)
        return 0

    enriched = 0
    skipped = 0

    for file in os.listdir(RAW_DIR):
        if not file.endswith(".json") or file.startswith("."):
            continue

        path = os.path.join(RAW_DIR, file)
        with open(path, "r") as f:
            data = json.load(f)

        current_summary = data.get("summary_raw", "")
        if len(current_summary) >= MIN_SUMMARY_LENGTH:
            skipped += 1
            continue

        url = data.get("url")
        if not url:
            continue

        logger.info("Scraping: %s (%d chars -> enriching)", url, len(current_summary))
        content = scrape_article(url)

        if content and len(content) > len(current_summary):
            data["summary_raw"] = content[:5000]
            data["enriched"] = True

            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            enriched += 1
            logger.info("Enriched: %s (%d -> %d chars)", file, len(current_summary), len(content[:5000]))
        else:
            logger.warning("Scrape returned less content than RSS for %s", file)

    logger.info("Enrichment complete: %d enriched, %d already sufficient", enriched, skipped)
    return enriched


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    update_raw_files()
