#!/usr/bin/env python3
"""
Standalone phantom persona engagement.

Runs a phantom persona (e.g., Marcus Chen) to comment on a specific
user's recent LinkedIn posts. Independent of the orchestrator — can be
triggered at any time.

Usage:
    python engagement/phantom.py --persona "The Visionary Advisor" --target kylebartlettai --dry-run
    python engagement/phantom.py --persona "The Visionary Advisor" --target kylebartlettai
    python engagement/phantom.py --persona "The Visionary Advisor" --target kylebartlettai --max-comments 2
    python engagement/phantom.py --persona "The Visionary Advisor" --target MainUser --no-headless
"""

import argparse
import asyncio
import logging
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add project root to path so this can run as a standalone script
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from browser.context_manager import PersonaContext
from browser.linkedin_actions import (
    get_feed_posts,
    comment_on_post,
    check_for_challenge,
    LinkedInChallengeDetected,
)
from config import load_personas
from engagement.quality_checker import check_quality
from engagement.tracker import log_comment
from llm.provider import generate_comment as llm_generate_comment
from summarization.safety_filter import violates_safety
from utils.kill_switch import check_kill_switch, activate_kill_switch

logger = logging.getLogger(__name__)


def _resolve_target(target: str) -> Optional[str]:
    """Resolve a target to a LinkedIn activity page URL.

    Accepts:
      - A persona name (e.g., "MainUser") → looks up linkedin_url in config
      - A LinkedIn slug (e.g., "kylebartlettai")
      - A full LinkedIn URL
    """
    # Full URL
    if target.startswith("http"):
        url = target.rstrip("/")
        if "/recent-activity/" not in url:
            url += "/recent-activity/all/"
        return url

    # Persona name lookup
    personas = load_personas()
    persona = next((p for p in personas if p["name"] == target), None)
    if persona:
        linkedin_url = persona.get("linkedin_url", "")
        if not linkedin_url:
            logger.error(
                "Persona '%s' has no linkedin_url set in config/personas.json. "
                "Pass a LinkedIn slug or URL instead (e.g., --target kylebartlettai)",
                target,
            )
            return None
        url = linkedin_url.rstrip("/")
        if "/recent-activity/" not in url:
            url += "/recent-activity/all/"
        return url

    # Treat as LinkedIn slug
    return f"https://www.linkedin.com/in/{target}/recent-activity/all/"


async def run_phantom_on_post(
    persona_name: str,
    target: str,
    max_comments: int = 1,
    headless: bool = True,
    dry_run: bool = False,
) -> list[dict]:
    """Run phantom persona engagement on a target user's posts.

    Args:
        persona_name: Phantom persona name (e.g., "The Visionary Advisor").
        target: LinkedIn slug, full URL, or persona name to target.
        max_comments: Maximum comments to post (default: 1).
        headless: Run browser in headless mode.
        dry_run: Generate comments but don't post them.

    Returns:
        List of comment result dicts.
    """
    if check_kill_switch():
        logger.warning("Kill switch active, aborting phantom engagement")
        return []

    # Load phantom persona
    personas = load_personas()
    persona = next((p for p in personas if p["name"] == persona_name), None)
    if not persona:
        logger.error("Persona not found: %s", persona_name)
        return []

    if persona["name"] == "MainUser":
        logger.error("Cannot run phantom engagement as MainUser — use a phantom persona")
        return []

    # Resolve target URL
    activity_url = _resolve_target(target)
    if not activity_url:
        return []

    logger.info(
        "Phantom engagement: %s (%s) → %s",
        persona["name"],
        persona.get("display_name", ""),
        activity_url,
    )

    results = []

    async with PersonaContext(persona_name, headless=headless) as ctx:
        page = await ctx.new_page()

        try:
            response = await page.goto(activity_url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(2.0, 4.0))

            if await check_for_challenge(page):
                activate_kill_switch()
                raise LinkedInChallengeDetected(
                    f"Challenge detected for {persona_name} on {activity_url}"
                )

            if "/404" in page.url or (response and response.status == 404):
                logger.error("Target profile not found: %s", target)
                return []

            posts = await get_feed_posts(page, max_posts=5)
            if not posts:
                logger.warning("No posts found on activity page: %s", activity_url)
                return []

            logger.info("Found %d posts on target's activity page", len(posts))

            for i, post in enumerate(posts[:max_comments]):
                if check_kill_switch():
                    logger.warning("Kill switch activated mid-run")
                    break

                if not post.get("text"):
                    continue

                logger.info(
                    "Generating comment %d/%d on post: %s...",
                    i + 1, max_comments, post["text"][:60],
                )

                comment = _generate_phantom_comment(post["text"], persona)
                if not comment:
                    logger.warning("LLM returned no comment, skipping post")
                    continue

                # Quality check with retry
                quality = check_quality(comment, post["text"])
                if not quality.passed:
                    logger.warning(
                        "Quality check failed (score=%d): %s",
                        quality.score, quality.violations,
                    )
                    comment = _generate_phantom_comment(
                        post["text"], persona,
                        feedback=f"Avoid: {', '.join(quality.violations)}",
                    )
                    if not comment:
                        continue
                    quality = check_quality(comment, post["text"])
                    if not quality.passed:
                        logger.warning("Retry also failed quality (score=%d), skipping", quality.score)
                        continue

                if violates_safety(comment):
                    logger.warning("Comment blocked by safety filter")
                    continue

                if dry_run:
                    logger.info(
                        "[DRY RUN] %s would comment:\n  %s",
                        persona.get("display_name", persona["name"]),
                        comment,
                    )
                else:
                    success = await comment_on_post(page, post["element_index"], comment)
                    if not success:
                        logger.error("Failed to post comment via Playwright")
                        continue
                    logger.info(
                        "POSTED as %s: %s",
                        persona.get("display_name", persona["name"]),
                        comment[:80],
                    )

                result = {
                    "persona": persona["name"],
                    "display_name": persona.get("display_name", ""),
                    "target": target,
                    "post_author": post.get("author", target),
                    "post_text": post["text"][:200],
                    "comment": comment,
                    "quality_score": quality.score,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "dry_run": dry_run,
                }
                results.append(result)

                log_comment(
                    persona=persona["name"],
                    author=post.get("author", target),
                    post_url=activity_url,
                    post_summary=post["text"][:60],
                    comment_text=comment,
                )

                # Delay between comments (natural pacing)
                if i < max_comments - 1 and i < len(posts) - 1:
                    delay = random.randint(120, 300)
                    logger.info("Waiting %d seconds before next comment", delay)
                    await asyncio.sleep(delay)

        except LinkedInChallengeDetected:
            logger.error("LinkedIn challenge detected — kill switch activated")
        except Exception as e:
            logger.error("Phantom engagement error: %s", e, exc_info=True)

    return results


def _generate_phantom_comment(
    post_text: str,
    persona: dict,
    feedback: str = "",
) -> Optional[str]:
    """Generate an in-character comment for a phantom persona."""
    style = random.choice([
        "direct_value_add",
        "direct_value_add",
        "thoughtful_question",
        "experience_share",
        "simple_agreement_with_specificity",
    ])

    length_instruction = random.choice([
        "Keep it to 2-3 sentences.",
        "Write 2-3 sentences.",
        "Write 3-4 sentences.",
    ])

    comment = llm_generate_comment(
        post_text=post_text,
        persona_system_prompt=persona.get("system_prompt", ""),
        style=style,
        length_instruction=length_instruction,
        feedback=feedback,
    )
    if comment:
        # Replace em dashes with regular dashes for natural LinkedIn tone
        comment = comment.replace("\u2014", "-").replace("\u2013", "-")
    return comment


def main():
    parser = argparse.ArgumentParser(
        description="Run phantom persona engagement on a target's LinkedIn posts",
    )
    parser.add_argument(
        "--persona",
        required=True,
        help='Phantom persona name (e.g., "The Visionary Advisor")',
    )
    parser.add_argument(
        "--target",
        required=True,
        help='LinkedIn slug (e.g., "kylebartlettai"), full URL, or persona name (e.g., "MainUser")',
    )
    parser.add_argument(
        "--max-comments",
        type=int,
        default=1,
        help="Maximum comments to post (default: 1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate comments but don't post them",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show browser window (useful for debugging)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    results = asyncio.run(
        run_phantom_on_post(
            persona_name=args.persona,
            target=args.target,
            max_comments=args.max_comments,
            headless=not args.no_headless,
            dry_run=args.dry_run,
        )
    )

    if results:
        print(f"\n=== {len(results)} comment(s) {'generated' if args.dry_run else 'posted'} ===")
        for r in results:
            status = "DRY RUN" if r["dry_run"] else "LIVE"
            print(f"  [{status}] {r['display_name']} → {r['post_author']}")
            print(f"    Score: {r['quality_score']} | {r['comment'][:100]}")
    else:
        print("\nNo comments generated.")


if __name__ == "__main__":
    main()
