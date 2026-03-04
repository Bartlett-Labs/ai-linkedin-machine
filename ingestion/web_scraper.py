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
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


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


def update_raw_files() -> None:
    """Enrich raw articles that have empty summaries by scraping the source URL."""
    if not os.path.isdir(RAW_DIR):
        logger.warning("Raw directory does not exist: %s", RAW_DIR)
        return

    for file in os.listdir(RAW_DIR):
        if not file.endswith(".json"):
            continue

        path = os.path.join(RAW_DIR, file)
        with open(path, "r") as f:
            data = json.load(f)

        if not data.get("summary_raw"):
            url = data.get("url")
            if url:
                logger.info("Scraping: %s", url)
                content = scrape_article(url)
                data["summary_raw"] = content[:5000]

                with open(path, "w") as f:
                    json.dump(data, f, indent=2)
                logger.info("Updated: %s", path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    update_raw_files()
