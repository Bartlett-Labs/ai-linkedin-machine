"""
RSS feed ingestion.

Reads feed URLs from config/feeds.json, fetches articles via feedparser,
and saves them to queue/incoming_raw/ as JSON files.

Freshness-first strategy: only ingests articles published within the
last `max_age_days` days. Uses a persistent hash manifest for dedup
that survives file archiving.
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
SEEN_HASHES_PATH = project_path("queue", "incoming_raw", ".seen_hashes.json")


def load_feeds():
    with open(CONFIG_PATH, "r") as f:
        data = json.load(f)
    return data["sources"]


def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _load_seen_hashes():
    """Load the set of previously ingested article hashes."""
    if os.path.exists(SEEN_HASHES_PATH):
        try:
            with open(SEEN_HASHES_PATH, "r") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, TypeError):
            pass
    return set()


def _save_seen_hashes(hashes):
    """Persist the seen hashes set."""
    with open(SEEN_HASHES_PATH, "w") as f:
        json.dump(sorted(hashes), f)


def _parse_entry_date(entry):
    """Extract publication date from a feedparser entry.

    Tries published_parsed, updated_parsed, then returns None.
    """
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                return datetime.datetime(*parsed[:6])
            except (TypeError, ValueError):
                continue
    return None


def save_article(article, source_name):
    title = article.get("title", "untitled")
    link = article.get("link")
    published = article.get("published", str(datetime.datetime.utcnow()))
    summary = article.get("summary", "")

    if not link:
        logger.warning("Skipping article with no link from %s", source_name)
        return None

    key = hash_text(link)
    out_path = os.path.join(OUTPUT_DIR, f"{key}.json")

    # Skip if file already exists
    if os.path.exists(out_path):
        return None

    payload = {
        "source": source_name,
        "title": title,
        "url": link,
        "published": published,
        "summary_raw": summary,
        "ingested_at": datetime.datetime.utcnow().isoformat(),
    }

    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    logger.info("Saved -> %s (%s)", out_path, title[:60])
    return key


def ingest(max_age_days: int = 7):
    """Ingest fresh articles from RSS feeds.

    - Only ingests articles published within the last max_age_days
    - Uses a persistent hash manifest for dedup (survives file archiving)
    - No flat cap: all fresh content gets ingested
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    feeds = load_feeds()
    seen = _load_seen_hashes()
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=max_age_days)

    total_new = 0
    total_skipped_old = 0
    total_skipped_seen = 0

    for feed in feeds:
        if feed["type"] != "rss":
            continue

        logger.info("Fetching: %s", feed["name"])
        try:
            parsed = feedparser.parse(feed["url"])
            feed_new = 0
            feed_old = 0
            feed_seen = 0

            for entry in parsed.entries:
                link = entry.get("link")
                if not link:
                    continue

                key = hash_text(link)

                # Dedup via persistent manifest (survives archiving)
                if key in seen:
                    feed_seen += 1
                    continue

                # Recency filter
                pub_date = _parse_entry_date(entry)
                if pub_date and pub_date < cutoff:
                    feed_old += 1
                    seen.add(key)  # Remember old articles too
                    continue

                result = save_article(entry, feed["name"])
                if result:
                    seen.add(key)
                    feed_new += 1

            logger.info("  %s: %d new, %d old (>%dd), %d already seen",
                        feed["name"], feed_new, feed_old, max_age_days, feed_seen)
            total_new += feed_new
            total_skipped_old += feed_old
            total_skipped_seen += feed_seen

        except Exception as e:
            logger.error("Failed to fetch feed %s: %s", feed["name"], e)

    _save_seen_hashes(seen)
    logger.info("Ingestion complete: %d new, %d skipped (old), %d skipped (seen)",
                total_new, total_skipped_old, total_skipped_seen)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingest()
