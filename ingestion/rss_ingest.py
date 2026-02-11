"""
RSS feed ingestion.

Reads feed URLs from config/feeds.json, fetches articles via feedparser,
and saves them to queue/incoming_raw/ as JSON files.
"""

import datetime
import hashlib
import json
import logging
import os

import feedparser

from utils import project_path

logger = logging.getLogger(__name__)

CONFIG_PATH = project_path("config", "feeds.json")
OUTPUT_DIR = project_path("queue", "incoming_raw")


def load_feeds():
    with open(CONFIG_PATH, "r") as f:
        data = json.load(f)
    return data["sources"]


def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def save_article(article, source_name):
    title = article.get("title", "untitled")
    link = article.get("link")
    published = article.get("published", str(datetime.datetime.utcnow()))
    summary = article.get("summary", "")

    if not link:
        logger.warning("Skipping article with no link from %s", source_name)
        return

    key = hash_text(link)
    out_path = os.path.join(OUTPUT_DIR, f"{key}.json")

    # Skip if already ingested
    if os.path.exists(out_path):
        return

    payload = {
        "source": source_name,
        "title": title,
        "url": link,
        "published": published,
        "summary_raw": summary,
        "ingested_at": str(datetime.datetime.utcnow()),
    }

    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    logger.info("Saved -> %s (%s)", out_path, title[:60])


def ingest():
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    feeds = load_feeds()

    for feed in feeds:
        if feed["type"] != "rss":
            continue

        logger.info("Fetching: %s", feed["name"])
        try:
            parsed = feedparser.parse(feed["url"])
            for entry in parsed.entries:
                save_article(entry, feed["name"])
        except Exception as e:
            logger.error("Failed to fetch feed %s: %s", feed["name"], e)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingest()
