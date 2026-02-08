#!/usr/bin/env python3
"""
AI LinkedIn Machine - Main Async Pipeline

Runs the full pipeline:
1. Sync queue from Google Sheet
2. Ingest RSS feeds (sync, no browser)
3. Summarize + generate posts (sync, API calls)
4. Execute OutboundQueue items via Playwright (async)
5. Run persona engagement (async, per-persona context)
6. Check replies (async)
7. Update Sheet with results
"""

import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent))

from sheets.client import SheetsClient
from sheets.models import EngineMode
from scheduling.orchestrator import run_orchestrator
from engagement.commenter import run_commenter
from engagement.replier import run_replier
from ingestion.rss_ingest import ingest
from summarization.summarize import run_all as run_summarize
from posting_generator.generate_post import run_all as generate_posts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/ai-linkedin-machine.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)


async def main(
    skip_ingest: bool = False,
    skip_generate: bool = False,
    dry_run: bool = False,
    headless: bool = True,
    comments_only: bool = False,
    replies_only: bool = False,
):
    """Run the full async pipeline."""
    logger.info("Starting AI LinkedIn Machine...")

    # Ensure required directories exist
    for d in ["logs", "queue/incoming_raw", "queue/summaries", "queue/posts",
              "queue/engagement", "tracking/linkedin"]:
        Path(d).mkdir(parents=True, exist_ok=True)

    # Connect to Google Sheet
    sheets_client = None
    try:
        sheets_client = SheetsClient()
        engine = sheets_client.get_engine_control()
        logger.info("Connected to Sheet. Mode: %s, Phase: %s",
                     engine.mode.value, engine.phase.value)

        if engine.mode == EngineMode.PAUSED:
            logger.info("Engine is PAUSED. Exiting.")
            return

        if engine.mode == EngineMode.DRY_RUN:
            dry_run = True
            logger.info("Engine in DRY_RUN mode")

    except Exception as e:
        logger.warning("Could not connect to Sheet (running offline): %s", e)

    # Handle single-action modes
    if comments_only:
        logger.info("Running comments only...")
        results = await run_commenter(
            sheets_client=sheets_client,
            headless=headless,
            dry_run=dry_run,
        )
        logger.info("Comments complete: %d actions", len(results))
        return

    if replies_only:
        logger.info("Running replies only...")
        results = await run_replier(
            sheets_client=sheets_client,
            headless=headless,
            dry_run=dry_run,
        )
        logger.info("Replies complete: %d actions", len(results))
        return

    # Step 1: Ingest RSS feeds (sync)
    if not skip_ingest:
        logger.info("Step 1: Ingesting RSS feeds...")
        try:
            ingest()
        except Exception as e:
            logger.error("RSS ingestion failed: %s", e)

    # Step 2: Summarize articles (sync, API calls)
    if not skip_generate:
        logger.info("Step 2: Summarizing articles...")
        try:
            run_summarize()
        except Exception as e:
            logger.error("Summarization failed: %s", e)

        # Step 3: Generate LinkedIn posts
        logger.info("Step 3: Generating LinkedIn posts...")
        try:
            generate_posts()
        except Exception as e:
            logger.error("Post generation failed: %s", e)

    # Step 4-7: Run the orchestrator (handles posting, engagement, replies)
    logger.info("Step 4: Running orchestrator...")
    summary = await run_orchestrator(
        sheets_client=sheets_client,
        headless=headless,
    )

    logger.info("Pipeline complete! Summary: %s", summary)


def parse_args():
    parser = argparse.ArgumentParser(description="AI LinkedIn Machine")
    parser.add_argument("--skip-ingest", action="store_true",
                        help="Skip RSS ingestion step")
    parser.add_argument("--skip-generate", action="store_true",
                        help="Skip summarization and post generation")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate but don't execute actions")
    parser.add_argument("--no-headless", action="store_true",
                        help="Show browser windows (for debugging)")
    parser.add_argument("--comments-only", action="store_true",
                        help="Only run the commenter")
    parser.add_argument("--replies-only", action="store_true",
                        help="Only run the replier")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        main(
            skip_ingest=args.skip_ingest,
            skip_generate=args.skip_generate,
            dry_run=args.dry_run,
            headless=not args.no_headless,
            comments_only=args.comments_only,
            replies_only=args.replies_only,
        )
    )
