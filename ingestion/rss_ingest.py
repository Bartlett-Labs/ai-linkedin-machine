import os, json, feedparser, hashlib, datetime
from dateutil.parser import parse as parse_date

CONFIG_PATH = "config/feeds.json"
OUTPUT_DIR = "queue/incoming_raw/"

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

    key = hash_text(link)

    out_path = os.path.join(OUTPUT_DIR, f"{key}.json")

    payload = {
        "source": source_name,
        "title": title,
        "url": link,
        "published": published,
        "summary_raw": summary,
        "ingested_at": str(datetime.datetime.utcnow())
    }

    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"[+] Saved → {out_path}")

def ingest():
    feeds = load_feeds()

    for feed in feeds:
        if feed["type"] != "rss":
            continue

        print(f"Fetching: {feed['name']}")
        parsed = feedparser.parse(feed["url"])

        for entry in parsed.entries:
            save_article(entry, feed["name"])

if __name__ == "__main__":
    ingest()
