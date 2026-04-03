"""
Article summarization pipeline.

Reads articles from queue/incoming_raw/, summarizes via LLM,
runs safety checks, and writes to queue/summaries/.

Freshness-first strategy: processes newest articles first, skips
already-summarized articles, and only processes articles ingested
within the last `max_age_days` days.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from summarization.safety_filter import violates_safety
from llm.provider import summarize as llm_summarize, generate as llm_generate
from utils import project_path

logger = logging.getLogger(__name__)

RAW_DIR = project_path("queue", "incoming_raw")
OUT_DIR = project_path("queue", "summaries")
PROMPT_PATH = project_path("summarization", "prompt_templates", "default.txt")
SAFETY_PROMPT_PATH = project_path("summarization", "prompt_templates", "employer_neutral.txt")


def load_prompt():
    with open(PROMPT_PATH, "r") as f:
        return f.read()


def load_safety_prompt():
    with open(SAFETY_PROMPT_PATH, "r") as f:
        return f.read()


def summarize_article(article_path):
    with open(article_path, "r") as f:
        data = json.load(f)

    article_text = data.get("summary_raw", "")
    prompt_template = load_prompt()

    # PRIMARY SUMMARY PASS (Claude -> OpenAI fallback)
    text = llm_summarize(article_text, prompt_template)

    if not text:
        logger.error("All LLM providers failed for %s", article_path)
        return

    # SAFETY PASS
    if violates_safety(text):
        safety_prompt = load_safety_prompt()
        rewritten = llm_generate(
            safety_prompt + "\n" + text,
            system_prompt="You are a safety rewriter for LinkedIn content.",
            max_tokens=800,
            temperature=0.3,
        )
        if rewritten:
            text = rewritten

    # WRITE OUTPUT
    os.makedirs(OUT_DIR, exist_ok=True)
    out_name = os.path.basename(article_path).replace(".json", ".md")
    out_path = os.path.join(OUT_DIR, out_name)

    with open(out_path, "w") as f:
        f.write(text)

    logger.info("Summarized -> %s", out_path)


def _get_ingested_at(filepath: str) -> datetime:
    """Extract ingested_at from article JSON, fall back to file mtime."""
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        ts = data.get("ingested_at", "")
        if ts:
            return datetime.fromisoformat(ts)
    except Exception:
        pass
    return datetime.fromtimestamp(os.path.getmtime(filepath))


def run_all(max_age_days: int = 7):
    """Summarize fresh articles using a freshness-first strategy.

    - Sorts articles by ingested_at (newest first)
    - Skips articles that already have a summary file
    - Only processes articles ingested within the last max_age_days
    - No flat cap: all fresh content gets summarized
    """
    if not os.path.exists(RAW_DIR):
        logger.warning("No raw articles directory: %s", RAW_DIR)
        return

    cutoff = datetime.now() - timedelta(days=max_age_days)

    # Collect articles with their ingestion timestamps
    articles: list[tuple[str, datetime]] = []
    for file in os.listdir(RAW_DIR):
        if not file.endswith(".json") or file.startswith("."):
            continue
        # Skip if already summarized
        summary_name = file.replace(".json", ".md")
        if os.path.exists(os.path.join(OUT_DIR, summary_name)):
            continue
        filepath = os.path.join(RAW_DIR, file)
        ingested_at = _get_ingested_at(filepath)
        if ingested_at < cutoff:
            continue
        articles.append((filepath, ingested_at))

    # Sort newest first
    articles.sort(key=lambda x: x[1], reverse=True)

    if not articles:
        logger.info("No fresh articles to summarize (checked %s, cutoff %dd)",
                     RAW_DIR, max_age_days)
        return

    logger.info("Summarizing %d fresh articles (of %d total in queue, cutoff %dd)",
                len(articles),
                len([f for f in os.listdir(RAW_DIR) if f.endswith(".json")]),
                max_age_days)

    for filepath, ingested_at in articles:
        summarize_article(filepath)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_all()
