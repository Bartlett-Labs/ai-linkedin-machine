"""
Coordinated multi-persona orchestrator.

The main coordinator that:
1. Reads current phase/mode from Sheet EngineControl
2. Reads rate limits for the current phase
3. Executes MainUser posts from OutboundQueue
4. Triggers phantom persona engagement after randomized delays
5. Runs MainUser commenting on targets
6. Checks replies on MainUser's existing posts
7. Logs all actions to Sheet SystemLog
"""

import asyncio
import json
import logging
import os
import random
from datetime import datetime

import yaml

from browser.context_manager import ContextPool
from browser.linkedin_actions import (
    navigate_to_feed,
    create_post,
    like_post,
    get_feed_posts,
    LinkedInChallengeDetected,
)
from engagement.commenter import run_commenter
from engagement.replier import run_replier
from engagement.tracker import log_post, log_like
from sheets.client import SheetsClient
from sheets.models import QueueStatus, EngineMode, Phase
from summarization.safety_filter import violates_safety, load_sheet_terms
from utils.kill_switch import check_kill_switch, activate_kill_switch
from utils.dedup import deduplicate_queue

logger = logging.getLogger(__name__)

RATE_LIMITS_PATH = "config/rate_limits.yaml"
PERSONAS_CONFIG = "config/personas.json"


def _load_rate_limits() -> dict:
    with open(RATE_LIMITS_PATH, "r") as f:
        return yaml.safe_load(f)


def _load_personas() -> list[dict]:
    with open(PERSONAS_CONFIG, "r") as f:
        return json.load(f)["personas"]


def _get_phantom_personas() -> list[dict]:
    """Get all personas except MainUser."""
    return [p for p in _load_personas() if p["name"] != "MainUser"]


async def run_orchestrator(
    sheets_client: SheetsClient = None,
    headless: bool = True,
) -> dict:
    """Run one full orchestration cycle.

    Returns a summary dict of actions taken.
    """
    summary = {
        "posts": 0,
        "comments": 0,
        "replies": 0,
        "phantom_actions": 0,
        "errors": [],
        "mode": "unknown",
        "phase": "unknown",
    }

    # 0. Check kill switch FIRST
    if check_kill_switch():
        logger.warning("Kill switch is active, aborting orchestration")
        summary["errors"].append("Kill switch active")
        return summary

    # Initialize Sheet client if not provided
    if sheets_client is None:
        try:
            sheets_client = SheetsClient()
        except Exception as e:
            logger.error("Could not connect to Google Sheet: %s", e)
            summary["errors"].append(f"Sheet connection failed: {e}")
            return summary

    # Load safety terms from Sheet into the safety filter
    try:
        load_sheet_terms(sheets_client)
    except Exception:
        pass  # Hardcoded terms still work

    # Deduplicate post queue before executing
    try:
        deduped = deduplicate_queue()
        if deduped:
            logger.info("Removed %d duplicate posts from queue", deduped)
    except Exception:
        pass

    # 1. Read engine control settings
    try:
        engine = sheets_client.get_engine_control()
    except Exception as e:
        logger.error("Could not read EngineControl: %s", e)
        summary["errors"].append(f"EngineControl read failed: {e}")
        return summary

    summary["mode"] = engine.mode.value
    summary["phase"] = engine.phase.value

    if engine.mode == EngineMode.PAUSED:
        logger.info("Engine is PAUSED, skipping cycle")
        sheets_client.log("ORCHESTRATOR", status="SKIPPED", details="Engine paused")
        return summary

    dry_run = engine.mode == EngineMode.DRY_RUN
    if dry_run:
        logger.info("Running in DRY RUN mode")

    # 2. Load rate limits for current phase
    rate_limits = _load_rate_limits().get(engine.phase.value, {})
    logger.info("Phase: %s, Mode: %s", engine.phase.value, engine.mode.value)

    sheets_client.log(
        "ORCHESTRATOR_START",
        details=f"Phase={engine.phase.value}, Mode={engine.mode.value}",
    )

    # 3. Execute MainUser posts from OutboundQueue
    if engine.main_user_posting:
        try:
            posts_made = await _execute_queue_posts(
                sheets_client, rate_limits, headless, dry_run
            )
            summary["posts"] = posts_made
        except LinkedInChallengeDetected as e:
            logger.error("Challenge detected during posting: %s", e)
            activate_kill_switch(f"LinkedIn challenge: {e}")
            summary["errors"].append(f"Challenge: {e}")
            sheets_client.log("CHALLENGE_DETECTED", "MainUser", status="BLOCKED", error=str(e))
            return summary

    # Check kill switch between major steps
    if check_kill_switch():
        return summary

    # 4. Phantom persona engagement on MainUser's recent posts
    if engine.phantom_engagement and summary["posts"] > 0:
        try:
            phantom_actions = await _run_phantom_engagement(
                sheets_client, rate_limits, headless, dry_run
            )
            summary["phantom_actions"] = phantom_actions
        except LinkedInChallengeDetected as e:
            logger.error("Challenge on phantom persona: %s", e)
            sheets_client.log("CHALLENGE_DETECTED", status="BLOCKED", error=str(e))

    if check_kill_switch():
        return summary

    # 5. MainUser commenting on targets
    if engine.commenting:
        max_comments = rate_limits.get("main_comments_per_day", 10)
        try:
            results = await run_commenter(
                sheets_client=sheets_client,
                persona_name="MainUser",
                max_comments=max_comments,
                headless=headless,
                dry_run=dry_run,
            )
            summary["comments"] = len(results)
        except LinkedInChallengeDetected as e:
            logger.error("Challenge during commenting: %s", e)
            activate_kill_switch(f"LinkedIn challenge: {e}")
            summary["errors"].append(f"Challenge: {e}")
            return summary
        except Exception as e:
            logger.error("Commenter failed: %s", e)
            summary["errors"].append(f"Commenter: {e}")

    if check_kill_switch():
        return summary

    # 6. Check replies on MainUser's posts
    if engine.replying:
        try:
            results = await run_replier(
                sheets_client=sheets_client,
                headless=headless,
                dry_run=dry_run,
            )
            summary["replies"] = len(results)
        except LinkedInChallengeDetected as e:
            logger.error("Challenge during replying: %s", e)
            activate_kill_switch(f"LinkedIn challenge: {e}")
            summary["errors"].append(f"Challenge: {e}")
        except Exception as e:
            logger.error("Replier failed: %s", e)
            summary["errors"].append(f"Replier: {e}")

    # 7. Update last run time
    try:
        sheets_client.update_last_run()
    except Exception:
        pass

    sheets_client.log(
        "ORCHESTRATOR_COMPLETE",
        details=(
            f"Posts={summary['posts']}, Comments={summary['comments']}, "
            f"Replies={summary['replies']}, Phantom={summary['phantom_actions']}"
        ),
        status="OK" if not summary["errors"] else "PARTIAL",
    )

    logger.info("Orchestration cycle complete: %s", summary)
    return summary


async def _execute_queue_posts(
    sheets_client: SheetsClient,
    rate_limits: dict,
    headless: bool,
    dry_run: bool,
) -> int:
    """Execute READY items from the OutboundQueue."""
    # Determine how many posts to make
    if "posts_per_day" in rate_limits:
        max_posts = rate_limits["posts_per_day"]
    elif "posts_per_week" in rate_limits:
        max_posts = 1  # At most 1 per run during stealth
    else:
        max_posts = 1

    items = sheets_client.get_ready_items(limit=max_posts)
    if not items:
        logger.info("No READY items in OutboundQueue")
        return 0

    posts_made = 0
    from browser.context_manager import PersonaContext

    for item in items:
        # Safety check on content
        if violates_safety(item.content):
            logger.warning("Queue item %s blocked by safety filter", item.post_id)
            sheets_client.update_queue_status(
                item, QueueStatus.SKIPPED, "Blocked by safety filter"
            )
            sheets_client.log(
                "POST_BLOCKED", item.persona, item.post_id,
                "SAFETY", "Content failed safety check",
            )
            continue

        if dry_run:
            logger.info(
                "[DRY RUN] Would post queue item %s: %s...",
                item.post_id, item.content[:80],
            )
            sheets_client.update_queue_status(item, QueueStatus.DONE, "DRY_RUN")
            sheets_client.log(
                "POST", item.persona, item.post_id, "DRY_RUN",
            )
            log_post(item.persona, item.content, queue_id=item.post_id)
            posts_made += 1
            continue

        # Execute the post via Playwright
        try:
            async with PersonaContext(item.persona, headless=headless) as ctx:
                page = await ctx.new_page()
                success = await create_post(page, item.content)

                if success:
                    sheets_client.update_queue_status(
                        item, QueueStatus.DONE, "Posted successfully"
                    )
                    sheets_client.log(
                        "POST", item.persona, item.post_id, "OK",
                    )
                    log_post(item.persona, item.content, queue_id=item.post_id)
                    posts_made += 1
                else:
                    sheets_client.update_queue_status(
                        item, QueueStatus.FAILED, "Playwright post failed"
                    )
                    sheets_client.log(
                        "POST_FAILED", item.persona, item.post_id, "FAILED",
                    )

        except Exception as e:
            logger.error("Failed to post item %s: %s", item.post_id, e)
            sheets_client.update_queue_status(
                item, QueueStatus.FAILED, str(e)
            )

        # Delay between posts
        if posts_made < len(items):
            delay = random.randint(
                rate_limits.get("min_delay_between_actions_sec", 300),
                rate_limits.get("min_delay_between_actions_sec", 300) + 120,
            )
            logger.info("Waiting %d seconds before next post", delay)
            await asyncio.sleep(delay)

    return posts_made


async def _run_phantom_engagement(
    sheets_client: SheetsClient,
    rate_limits: dict,
    headless: bool,
    dry_run: bool,
) -> int:
    """Run phantom persona engagement on MainUser's most recent post.

    Phantoms like and comment on the post after a randomized delay
    to simulate organic engagement (the "golden hour" strategy).
    """
    phantoms = _get_phantom_personas()
    if not phantoms:
        return 0

    max_phantom_comments = rate_limits.get("phantom_comments_per_post", 2)
    delay_range = rate_limits.get("phantom_delay_after_post_min", [2, 15])
    linkedin_phantoms = [
        p for p in phantoms
        if "linkedin" in p.get("behavior", {}).get("platforms", [])
    ]

    if not linkedin_phantoms:
        return 0

    # Select a subset of phantoms for this post
    selected = random.sample(
        linkedin_phantoms,
        min(max_phantom_comments, len(linkedin_phantoms)),
    )

    actions = 0

    for phantom in selected:
        # Randomized delay before this phantom engages
        delay_min = random.randint(delay_range[0], delay_range[1])
        delay_sec = delay_min * 60
        logger.info(
            "Phantom '%s' will engage in %d minutes",
            phantom["name"], delay_min,
        )

        if not dry_run:
            await asyncio.sleep(delay_sec)

        try:
            from browser.context_manager import PersonaContext

            async with PersonaContext(phantom["name"], headless=headless) as ctx:
                page = await ctx.new_page()
                await navigate_to_feed(page)
                posts = await get_feed_posts(page, max_posts=3)

                if not posts:
                    continue

                # Like the first post (our recent post should be near top)
                if dry_run:
                    logger.info(
                        "[DRY RUN] Phantom '%s' would like + comment",
                        phantom["name"],
                    )
                else:
                    await like_post(page, 0)
                    log_like(phantom["name"], posts[0].get("urn", ""), posts[0]["author"])

                # Comment
                comment_results = await run_commenter(
                    sheets_client=sheets_client,
                    persona_name=phantom["name"],
                    max_comments=1,
                    headless=headless,
                    dry_run=dry_run,
                )

                actions += 1 + len(comment_results)

                sheets_client.log(
                    "PHANTOM_ENGAGE",
                    phantom["name"],
                    status="DRY_RUN" if dry_run else "OK",
                    details=f"Like + {len(comment_results)} comments",
                )

        except Exception as e:
            logger.error("Phantom engagement failed for %s: %s", phantom["name"], e)
            sheets_client.log(
                "PHANTOM_FAILED", phantom["name"],
                status="FAILED", error=str(e),
            )

    return actions
