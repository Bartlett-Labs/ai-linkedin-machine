#!/usr/bin/env python3
"""
Per-persona autonomous heartbeat runner.

Each phantom persona runs independently on their own schedule,
commenting on feed posts, occasionally engaging with Kyle's posts,
and sometimes generating their own posts. This makes each persona
behave like a real LinkedIn user instead of only reacting to MainUser.

Usage:
    python scheduling/heartbeat.py --persona "The Visionary Advisor" --dry-run
    python scheduling/heartbeat.py --all --dry-run
    python scheduling/heartbeat.py --all
"""

import argparse
import asyncio
import logging
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from config import load_personas
from engagement.commenter import run_commenter
from engagement.phantom import run_phantom_on_post
from engagement.tracker import get_daily_stats
from llm.provider import generate
from posting.poster import post_single
from summarization.safety_filter import violates_safety
from utils.kill_switch import check_kill_switch

logger = logging.getLogger(__name__)

DEFAULT_SESSION_DIR = os.path.expanduser("~/.ai-linkedin-machine/sessions")


def _has_active_session(persona_name: str) -> bool:
    """Check if a persona has a saved browser session (logged in)."""
    safe_name = persona_name.lower().replace(" ", "_")
    session_path = os.path.join(DEFAULT_SESSION_DIR, safe_name)
    if not os.path.isdir(session_path):
        return False
    # Check for actual session data (not just an empty dir)
    return len(os.listdir(session_path)) > 0


def _is_in_active_hours(persona: dict) -> bool:
    """Check if the current time is within the persona's active hours."""
    active_hours = persona.get("active_hours")
    if not active_hours:
        return True  # No restriction = always active

    tz = ZoneInfo(active_hours["timezone"])
    now = datetime.now(tz)
    start_h, start_m = map(int, active_hours["start"].split(":"))
    end_h, end_m = map(int, active_hours["end"].split(":"))

    start_minutes = start_h * 60 + start_m
    end_minutes = end_h * 60 + end_m
    now_minutes = now.hour * 60 + now.minute

    return start_minutes <= now_minutes <= end_minutes


def _get_phantom_personas() -> list[dict]:
    """Return all non-MainUser personas."""
    personas = load_personas()
    return [p for p in personas if p["name"] != "MainUser"]


def _get_eligible_personas() -> list[dict]:
    """Return phantoms that have active sessions and are in their active hours."""
    phantoms = _get_phantom_personas()
    eligible = []
    for p in phantoms:
        if not _has_active_session(p["name"]):
            logger.debug("%s: no active session, skipping", p["display_name"])
            continue
        if not _is_in_active_hours(p):
            logger.debug("%s: outside active hours, skipping", p["display_name"])
            continue
        eligible.append(p)
    return eligible


async def _generate_persona_post(persona: dict) -> Optional[str]:
    """Generate a short LinkedIn post in the persona's voice."""
    topics = persona.get("engagement_rules", {}).get("triggers", [])
    if not topics:
        return None

    topic = random.choice(topics)
    prompt = (
        f"Write a short LinkedIn post (3-5 sentences) about: {topic}\n\n"
        "Rules:\n"
        "- Write in first person as if sharing a genuine observation or experience\n"
        "- No hashtags\n"
        "- No emojis\n"
        "- No engagement bait ('Agree?', 'Thoughts?', 'Repost if')\n"
        "- No self-promotion or calls to action\n"
        "- Sound like a real person, not a content marketer\n"
        "- Do NOT mention your name or identify yourself"
    )

    content = generate(
        prompt=prompt,
        system_prompt=persona.get("system_prompt", ""),
        max_tokens=300,
        temperature=0.8,
    )

    if content:
        content = content.replace("\u2014", "-").replace("\u2013", "-")
        if violates_safety(content):
            logger.warning("Generated post for %s blocked by safety filter", persona["display_name"])
            return None

    return content


async def run_persona_heartbeat(
    persona_name: str,
    dry_run: bool = False,
    headless: bool = True,
) -> dict:
    """Run one heartbeat cycle for a persona.

    A heartbeat cycle:
    1. Comment on feed posts (run_commenter)
    2. Maybe comment on Kyle's posts (run_phantom_on_post)
    3. Maybe generate and publish own post (post_single)

    Args:
        persona_name: The persona to run (e.g., "The Visionary Advisor").
        dry_run: If True, generate but don't post.
        headless: Run browser headless.

    Returns:
        Dict summarizing what happened this cycle.
    """
    personas = load_personas()
    persona = next((p for p in personas if p["name"] == persona_name), None)
    if not persona:
        logger.error("Persona not found: %s", persona_name)
        return {"persona": persona_name, "error": "not found"}

    if persona["name"] == "MainUser":
        logger.error("Heartbeat is for phantom personas, not MainUser")
        return {"persona": persona_name, "error": "mainuser not allowed"}

    if not _has_active_session(persona_name):
        logger.warning("%s has no active browser session", persona.get("display_name", persona_name))
        return {"persona": persona_name, "error": "no session"}

    if not _is_in_active_hours(persona):
        logger.info("%s is outside active hours, skipping", persona.get("display_name", persona_name))
        return {"persona": persona_name, "skipped": "outside active hours"}

    if check_kill_switch():
        logger.warning("Kill switch active, skipping heartbeat for %s", persona_name)
        return {"persona": persona_name, "skipped": "kill switch"}

    schedule = persona.get("schedule", {})
    comments_per_cycle = schedule.get("comments_per_cycle", 2)
    post_chance = schedule.get("post_chance_per_cycle", 0.1)
    kyle_chance = schedule.get("kyle_comment_chance", 0.2)

    # Check daily limits
    stats = get_daily_stats(persona=persona_name)
    behavior = persona.get("behavior", {})
    daily_comment_limit = behavior.get("comment_frequency", 5)
    daily_post_limit = behavior.get("post_frequency", 1)

    result = {
        "persona": persona_name,
        "display_name": persona.get("display_name", ""),
        "comments": [],
        "kyle_comments": [],
        "post": None,
        "dry_run": dry_run,
    }

    display = persona.get("display_name", persona_name)
    logger.info("=== Heartbeat: %s ===", display)

    # --- 1. Comment on feed posts ---
    comments_remaining = daily_comment_limit - stats["comments_posted"]
    if comments_remaining > 0:
        cycle_comments = min(comments_per_cycle, comments_remaining)
        logger.info("%s: commenting on %d feed posts (daily: %d/%d)",
                     display, cycle_comments, stats["comments_posted"], daily_comment_limit)
        try:
            feed_results = await run_commenter(
                persona_name=persona_name,
                max_comments=cycle_comments,
                headless=headless,
                dry_run=dry_run,
            )
            result["comments"] = feed_results
        except Exception as e:
            logger.error("%s: feed commenting failed: %s", display, e)
    else:
        logger.info("%s: daily comment limit reached (%d)", display, daily_comment_limit)

    if check_kill_switch():
        return result

    # --- 2. Maybe comment on Kyle's posts ---
    if random.random() < kyle_chance and comments_remaining > 0:
        logger.info("%s: commenting on Kyle's posts (chance: %.0f%%)", display, kyle_chance * 100)
        try:
            kyle_results = await run_phantom_on_post(
                persona_name=persona_name,
                target="kyle-bartlett",
                max_comments=1,
                headless=headless,
                dry_run=dry_run,
            )
            result["kyle_comments"] = kyle_results
        except Exception as e:
            logger.error("%s: Kyle commenting failed: %s", display, e)
    else:
        logger.debug("%s: skipping Kyle comment this cycle", display)

    if check_kill_switch():
        return result

    # --- 3. Maybe generate + post own content ---
    if random.random() < post_chance and stats["posts_made"] < daily_post_limit:
        logger.info("%s: generating a post (chance: %.0f%%)", display, post_chance * 100)
        try:
            content = await _generate_persona_post(persona)
            if content:
                if dry_run:
                    logger.info("[DRY RUN] %s would post:\n  %s", display, content[:200])
                    result["post"] = {"content": content[:200], "dry_run": True}
                else:
                    success = await post_single(content, persona_name=persona_name, headless=headless)
                    result["post"] = {"content": content[:200], "posted": success}
                    if success:
                        logger.info("POSTED by %s: %s", display, content[:80])
                    else:
                        logger.error("Failed to post for %s", display)
        except Exception as e:
            logger.error("%s: post generation failed: %s", display, e)
    else:
        logger.debug("%s: skipping post this cycle", display)

    logger.info("=== Heartbeat complete: %s — %d feed comments, %d kyle comments, post=%s ===",
                display,
                len(result["comments"]),
                len(result["kyle_comments"]),
                "yes" if result.get("post") else "no")

    return result


async def run_all_heartbeats(dry_run: bool = False, headless: bool = True) -> list[dict]:
    """Run heartbeat for all eligible personas (active session + active hours)."""
    eligible = _get_eligible_personas()

    if not eligible:
        logger.info("No eligible personas for heartbeat (no active sessions or outside hours)")
        return []

    logger.info("Running heartbeats for %d persona(s): %s",
                len(eligible),
                ", ".join(p.get("display_name", p["name"]) for p in eligible))

    results = []
    for persona in eligible:
        if check_kill_switch():
            logger.warning("Kill switch active, stopping all heartbeats")
            break

        result = await run_persona_heartbeat(
            persona_name=persona["name"],
            dry_run=dry_run,
            headless=headless,
        )
        results.append(result)

        # Stagger between personas (don't slam LinkedIn with multiple accounts)
        if len(eligible) > 1:
            delay = random.randint(120, 300)
            logger.info("Waiting %d seconds before next persona", delay)
            await asyncio.sleep(delay)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run per-persona heartbeat engagement cycles",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--persona",
        help='Run heartbeat for a specific persona (e.g., "The Visionary Advisor")',
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Run heartbeat for all eligible personas",
    )
    parser.add_argument("--dry-run", action="store_true", help="Generate but don't post")
    parser.add_argument("--no-headless", action="store_true", help="Show browser window")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    headless = not args.no_headless

    if args.all:
        results = asyncio.run(run_all_heartbeats(dry_run=args.dry_run, headless=headless))
        total_comments = sum(len(r.get("comments", [])) + len(r.get("kyle_comments", [])) for r in results)
        total_posts = sum(1 for r in results if r.get("post"))
        print(f"\n=== Heartbeat summary: {len(results)} persona(s), {total_comments} comments, {total_posts} posts ===")
        for r in results:
            if r.get("error") or r.get("skipped"):
                print(f"  {r.get('display_name', r['persona'])}: {r.get('error') or r.get('skipped')}")
            else:
                c = len(r.get("comments", [])) + len(r.get("kyle_comments", []))
                p = "yes" if r.get("post") else "no"
                print(f"  {r.get('display_name', r['persona'])}: {c} comments, post={p}")
    else:
        result = asyncio.run(
            run_persona_heartbeat(
                persona_name=args.persona,
                dry_run=args.dry_run,
                headless=headless,
            )
        )
        if result.get("error") or result.get("skipped"):
            print(f"\n{result.get('display_name', result['persona'])}: {result.get('error') or result.get('skipped')}")
        else:
            c = len(result.get("comments", [])) + len(result.get("kyle_comments", []))
            p = "yes" if result.get("post") else "no"
            print(f"\n=== {result.get('display_name', result['persona'])} heartbeat: {c} comments, post={p} ===")


if __name__ == "__main__":
    main()
