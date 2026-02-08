"""
LinkedIn poster - executes posts via Playwright with persistent persona contexts.

Reads post content from queue/posts/ directory or from Google Sheet
OutboundQueue. Uses browser automation with human-like behavior.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

from browser.context_manager import PersonaContext
from browser.linkedin_actions import create_post
from engagement.tracker import log_post
from summarization.safety_filter import violates_safety

logger = logging.getLogger(__name__)

POSTS_DIR = "queue/posts/"
PERSONAS_CONFIG = "config/personas.json"


def load_personas() -> list[dict]:
    with open(PERSONAS_CONFIG, "r") as f:
        return json.load(f)["personas"]


async def post_from_queue(
    persona_name: str = "MainUser",
    headless: bool = True,
    dry_run: bool = False,
    sheets_client=None,
) -> list[dict]:
    """Post all pending items from queue/posts/ directory.

    Args:
        persona_name: Which persona to post as.
        headless: Run browser headless.
        dry_run: Log but don't actually post.
        sheets_client: Optional SheetsClient for logging.

    Returns:
        List of result dicts.
    """
    results = []
    post_files = sorted(Path(POSTS_DIR).glob("*_post.txt"))

    if not post_files:
        logger.info("No posts in queue directory")
        return results

    async with PersonaContext(persona_name, headless=headless) as ctx:
        page = await ctx.new_page()

        for post_file in post_files:
            content = post_file.read_text().strip()
            if not content:
                continue

            # Safety check
            if violates_safety(content):
                logger.warning("Post blocked by safety filter: %s", post_file.name)
                _move_to_failed(post_file)
                continue

            if dry_run:
                logger.info("[DRY RUN] Would post: %s...", content[:80])
                result = {"file": post_file.name, "status": "dry_run", "content": content[:200]}
            else:
                success = await create_post(page, content)
                if success:
                    result = {"file": post_file.name, "status": "posted", "content": content[:200]}
                    _move_to_done(post_file)
                    logger.info("Posted: %s", post_file.name)
                else:
                    result = {"file": post_file.name, "status": "failed"}
                    _move_to_failed(post_file)
                    logger.error("Failed to post: %s", post_file.name)

            log_post(persona_name, content, queue_id=post_file.stem)
            results.append(result)

            if sheets_client:
                sheets_client.log(
                    "POST_FROM_QUEUE",
                    persona_name,
                    post_file.name,
                    result["status"].upper(),
                )

            # Delay between posts
            await asyncio.sleep(10)

    return results


def _move_to_done(file_path: Path) -> None:
    """Move a posted file to a done subdirectory."""
    done_dir = file_path.parent / "done"
    done_dir.mkdir(exist_ok=True)
    file_path.rename(done_dir / file_path.name)


def _move_to_failed(file_path: Path) -> None:
    """Move a failed file to a failed subdirectory."""
    failed_dir = file_path.parent / "failed"
    failed_dir.mkdir(exist_ok=True)
    file_path.rename(failed_dir / file_path.name)


async def post_single(
    content: str,
    persona_name: str = "MainUser",
    headless: bool = True,
) -> bool:
    """Post a single piece of content. Returns True on success."""
    if violates_safety(content):
        logger.error("Content blocked by safety filter")
        return False

    async with PersonaContext(persona_name, headless=headless) as ctx:
        page = await ctx.new_page()
        success = await create_post(page, content)
        if success:
            log_post(persona_name, content)
        return success


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(post_from_queue(dry_run=True))
