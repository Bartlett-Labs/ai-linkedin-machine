"""
LinkedIn commenter - finds and comments on target posts.

Pulls targets from Google Sheet (CommentTargets tab) or local config.
Uses Playwright with persistent persona contexts and human-like typing.
Validates every comment through quality_checker before posting.
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import Optional

from browser.context_manager import PersonaContext
from browser.linkedin_actions import (
    navigate_to_feed,
    scroll_feed,
    get_feed_posts,
    comment_on_post,
)
from config import load_personas
from engagement.quality_checker import check_quality
from engagement.tracker import get_daily_stats, log_comment
from engagement.lead_tracker import evaluate_lead, add_lead
from llm.provider import generate_comment as llm_generate_comment
from summarization.safety_filter import violates_safety
from utils.kill_switch import check_kill_switch

logger = logging.getLogger(__name__)


async def run_commenter(
    sheets_client=None,
    persona_name: str = "MainUser",
    max_comments: int = 10,
    headless: bool = True,
    dry_run: bool = False,
) -> list[dict]:
    """Run the commenting pipeline for a persona.

    Args:
        sheets_client: Optional SheetsClient for reading targets/templates.
        persona_name: Which persona to comment as.
        max_comments: Maximum comments to post in this run.
        headless: Run browser in headless mode.
        dry_run: If True, generate comments but don't post them.

    Returns:
        List of comment result dicts.
    """
    # Check daily limits
    stats = get_daily_stats()
    remaining = max_comments - stats["comments_posted"]
    if remaining <= 0:
        logger.info("Daily comment limit reached (%d posted)", stats["comments_posted"])
        return []

    # Load persona
    personas = load_personas()
    persona = next((p for p in personas if p["name"] == persona_name), personas[0])

    # Get targets from Sheet or use feed
    targets = []
    comment_templates = []
    if sheets_client:
        try:
            targets = sheets_client.get_comment_targets()
            comment_templates = sheets_client.get_comment_templates(persona_name)
        except Exception as e:
            logger.warning("Could not load from Sheet, using feed: %s", e)

    results = []

    async with PersonaContext(persona_name, headless=headless) as ctx:
        page = await ctx.new_page()

        if targets:
            # Interleave target visits with feed browsing for natural behavior.
            # Pattern: 2-3 feed comments → 1 target → feed scroll → 1 target → ...
            random.shuffle(targets)
            target_iter = iter(targets[:remaining])

            # Start with feed to look organic
            await navigate_to_feed(page)
            await scroll_feed(page, scrolls=2)
            feed_posts = await get_feed_posts(page, max_posts=15)
            feed_posts = [
                p for p in feed_posts
                if p["text"] and p["text"] not in [r.get("post_text", "")[:60] for r in stats.get("actions", [])]
            ]
            feed_iter = iter(feed_posts)

            actions_done = 0
            while actions_done < remaining:
                if check_kill_switch():
                    logger.warning("Kill switch activated, stopping commenter")
                    break

                # Every 3rd action, do a feed comment to look natural
                if actions_done > 0 and actions_done % 3 == 0:
                    feed_post = next(feed_iter, None)
                    if feed_post:
                        # Scroll feed first to simulate browsing
                        await navigate_to_feed(page)
                        await asyncio.sleep(random.uniform(2.0, 5.0))
                        result = await _comment_on_feed_post(
                            page, persona, feed_post, comment_templates,
                            stats, dry_run, sheets_client,
                        )
                        if result:
                            results.append(result)
                            actions_done += 1
                            delay = random.randint(180, 480)
                            logger.info("Waiting %d seconds (feed interleave)", delay)
                            await asyncio.sleep(delay)
                        continue

                # Target visit
                target = next(target_iter, None)
                if target is None:
                    break

                result = await _comment_on_target(
                    page, persona, target, comment_templates,
                    stats, dry_run, sheets_client,
                )
                if result:
                    results.append(result)
                    actions_done += 1
                    delay = random.randint(180, 480)
                    logger.info("Waiting %d seconds before next comment", delay)
                    await asyncio.sleep(delay)
        else:
            # No targets - pure feed commenting
            await navigate_to_feed(page)
            await scroll_feed(page, scrolls=2)
            posts = await get_feed_posts(page, max_posts=15)

            for post in posts[:remaining]:
                if check_kill_switch():
                    logger.warning("Kill switch activated, stopping commenter")
                    break

                if post["text"] and post["text"] not in [r.get("post_text", "")[:60] for r in stats.get("actions", [])]:
                    result = await _comment_on_feed_post(
                        page, persona, post, comment_templates,
                        stats, dry_run, sheets_client,
                    )
                    if result:
                        results.append(result)
                        delay = random.randint(180, 480)
                        logger.info("Waiting %d seconds before next comment", delay)
                        await asyncio.sleep(delay)

    return results


async def _comment_on_target(
    page,
    persona: dict,
    target,
    templates: list,
    stats: dict,
    dry_run: bool,
    sheets_client=None,
) -> Optional[dict]:
    """Navigate to a target's profile and comment on their latest post."""
    try:
        url = target.linkedin_url
        if not url:
            return None

        # Navigate to the target's recent activity
        activity_url = url.rstrip("/") + "/recent-activity/all/"
        await page.goto(activity_url, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(2.0, 4.0))

        # Get their posts
        posts = await get_feed_posts(page, max_posts=5)
        if not posts:
            logger.info("No posts found for target: %s", target.name)
            return None

        # Pick the most recent post
        post = posts[0]

        # Generate comment
        comment = _generate_comment(
            post["text"], persona, target.category, templates
        )
        if not comment:
            return None

        # Quality check
        recent_comments = [r.get("comment", "") for r in stats.get("actions", [])]
        quality = check_quality(comment, post["text"], recent_comments=recent_comments)
        if not quality.passed:
            logger.warning(
                "Comment failed quality check for %s: %s",
                target.name, quality.violations,
            )
            # Retry once with feedback
            comment = _generate_comment(
                post["text"], persona, target.category, templates,
                feedback=f"Avoid: {', '.join(quality.violations)}"
            )
            if not comment:
                return None
            quality = check_quality(comment, post["text"])
            if not quality.passed:
                logger.warning("Comment still failed quality on retry, skipping")
                return None

        # Safety check
        if violates_safety(comment):
            logger.warning("Comment blocked by safety filter for target: %s", target.name)
            return None

        # Post or dry-run
        if dry_run:
            logger.info("[DRY RUN] Would comment on %s's post: %s", target.name, comment[:80])
        else:
            success = await comment_on_post(page, 0, comment)
            if not success:
                logger.error("Failed to post comment on %s's post", target.name)
                if sheets_client:
                    sheets_client.log("COMMENT_FAILED", persona["name"], target.name, "FAILED")
                return None

        # Log
        result = {
            "target": target.name,
            "post_text": post["text"][:200],
            "comment": comment,
            "quality_score": quality.score,
            "timestamp": datetime.utcnow().isoformat(),
            "dry_run": dry_run,
        }

        log_comment(
            persona=persona["name"],
            author=target.name,
            post_url=target.linkedin_url,
            post_summary=post["text"][:60],
            comment_text=comment,
        )

        if sheets_client:
            sheets_client.log(
                "COMMENT",
                persona["name"],
                target.name,
                "DRY_RUN" if dry_run else "OK",
                f"Score: {quality.score}",
            )

        # Lead evaluation on post author
        lead = evaluate_lead(
            name=post["author"],
            post_url=target.linkedin_url,
            interaction_type="commented_on",
        )
        if lead:
            add_lead(lead)

        return result

    except Exception as e:
        logger.error("Error commenting on target %s: %s", target.name, e)
        return None


async def _comment_on_feed_post(
    page,
    persona: dict,
    post: dict,
    templates: list,
    stats: dict,
    dry_run: bool,
    sheets_client=None,
) -> Optional[dict]:
    """Comment on a post from the general feed."""
    try:
        comment = _generate_comment(
            post["text"], persona, "general", templates
        )
        if not comment:
            return None

        quality = check_quality(comment, post["text"])
        if not quality.passed:
            return None

        if violates_safety(comment):
            return None

        if dry_run:
            logger.info("[DRY RUN] Would comment on %s's post: %s",
                        post["author"], comment[:80])
        else:
            success = await comment_on_post(page, post["element_index"], comment)
            if not success:
                return None

        result = {
            "target": post["author"],
            "post_text": post["text"][:200],
            "comment": comment,
            "quality_score": quality.score,
            "timestamp": datetime.utcnow().isoformat(),
            "dry_run": dry_run,
        }

        log_comment(
            persona=persona["name"],
            author=post["author"],
            post_url="feed",
            post_summary=post["text"][:60],
            comment_text=comment,
        )

        if sheets_client:
            sheets_client.log(
                "COMMENT",
                persona["name"],
                post["author"],
                "DRY_RUN" if dry_run else "OK",
            )

        return result

    except Exception as e:
        logger.error("Error commenting on feed post: %s", e)
        return None


def _generate_comment(
    post_text: str,
    persona: dict,
    category: str,
    templates: list,
    feedback: str = "",
) -> Optional[str]:
    """Generate a comment using the LLM provider (Claude -> OpenAI -> templates).

    This is a synchronous function because the LLM provider calls are synchronous.
    """
    style = random.choice([
        "direct_value_add",
        "direct_value_add",
        "brief_acknowledgment",
        "thoughtful_question",
        "experience_share",
        "simple_agreement_with_specificity",
    ])

    length_instruction = random.choice([
        "Keep it to 1-2 sentences.",
        "Write 2-3 sentences.",
        "Write 2-3 sentences.",
        "Write 3-4 sentences.",
        "Write 4-5 sentences for a more detailed response.",
    ])

    # Build template fallback list from Sheet templates
    fallback_texts = [t.template_text for t in templates if t.template_text] if templates else None

    return llm_generate_comment(
        post_text=post_text,
        persona_system_prompt=persona.get("system_prompt", ""),
        style=style,
        length_instruction=length_instruction,
        feedback=feedback,
        fallback_templates=fallback_texts,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_commenter(dry_run=True))
