"""
LinkedIn replier - monitors and replies to comments on MainUser's posts.

Navigates to MainUser's own posts, finds new comments, checks them
against ReplyRules from the Sheet (BLOCK/REPLY triggers), generates
contextual replies, and posts them with human-like typing.
"""

import asyncio
import json
import logging
import os
import random
from datetime import datetime
from typing import Optional

from browser.context_manager import PersonaContext
from browser.linkedin_actions import (
    navigate_to_profile_posts,
    get_feed_posts,
    get_post_comments,
)
from config import load_personas
from engagement.quality_checker import check_quality
from engagement.tracker import get_daily_stats, log_reply
from engagement.lead_tracker import evaluate_lead, add_lead
from llm.provider import generate_reply as llm_generate_reply
from summarization.safety_filter import violates_safety
from utils import project_path
from utils.kill_switch import check_kill_switch

logger = logging.getLogger(__name__)

TRACKER_FILE = project_path("queue", "engagement", "reply_tracker.json")


def _load_reply_tracker() -> dict:
    """Load the set of already-replied-to comments."""
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, "r") as f:
            return json.load(f)
    return {"replied_to": []}


def _save_reply_tracker(tracker: dict) -> None:
    os.makedirs(os.path.dirname(TRACKER_FILE), exist_ok=True)
    with open(TRACKER_FILE, "w") as f:
        json.dump(tracker, f, indent=2)


async def run_replier(
    sheets_client=None,
    profile_slug: str = "",
    max_replies: int = 5,
    headless: bool = True,
    dry_run: bool = False,
) -> list[dict]:
    """Check MainUser's posts for new comments and reply.

    Args:
        sheets_client: Optional SheetsClient for reply rules.
        profile_slug: LinkedIn profile slug for MainUser.
        max_replies: Max replies per run.
        headless: Run headless.
        dry_run: Generate but don't post replies.

    Returns:
        List of reply result dicts.
    """
    stats = get_daily_stats()
    remaining = max_replies - stats["replies_sent"]
    if remaining <= 0:
        logger.info("Daily reply limit reached")
        return []

    # Load reply rules from Sheet
    reply_rules = []
    if sheets_client:
        try:
            reply_rules = sheets_client.get_reply_rules()
        except Exception as e:
            logger.warning("Could not load reply rules from Sheet: %s", e)

    # Load tracker to avoid double-replying
    tracker = _load_reply_tracker()
    replied_set = set(tracker.get("replied_to", []))

    persona = load_personas()[0]  # MainUser
    results = []

    async with PersonaContext("MainUser", headless=headless) as ctx:
        page = await ctx.new_page()

        if profile_slug:
            await navigate_to_profile_posts(page, profile_slug)
        else:
            # Navigate to "My posts" via activity page
            await page.goto(
                "https://www.linkedin.com/in/me/recent-activity/all/",
                wait_until="domcontentloaded",
            )
            await asyncio.sleep(random.uniform(2.0, 4.0))

        # Get our recent posts
        posts = await get_feed_posts(page, max_posts=10)

        for post in posts:
            if remaining <= 0:
                break
            if check_kill_switch():
                logger.warning("Kill switch activated, stopping replier")
                break

            # Click into the post to see comments
            try:
                from browser.linkedin_actions import SEL
                post_locators = page.locator(SEL["feed_post"])
                count = await post_locators.count()
                if post["element_index"] < count:
                    post_el = post_locators.nth(post["element_index"])
                    await post_el.scroll_into_view_if_needed()

                    comments = await get_post_comments(page, post["element_index"])

                    for comment_data in comments:
                        # Use author + text snippet as dedup key (URNs no longer available)
                        comment_key = f"{post['author']}:{comment_data['author']}:{comment_data['text'][:30]}"
                        if comment_key in replied_set:
                            continue

                        # Check reply rules
                        action = _check_reply_rules(
                            comment_data["text"], reply_rules
                        )

                        if action == "BLOCK":
                            logger.info(
                                "Blocked comment from %s (matched block rule)",
                                comment_data["author"],
                            )
                            replied_set.add(comment_key)
                            continue

                        if action == "IGNORE":
                            continue

                        # Generate reply
                        reply_text = _generate_reply(
                            comment_data["text"],
                            post["text"],
                            persona,
                        )

                        if not reply_text:
                            continue

                        # Safety check
                        if violates_safety(reply_text):
                            logger.warning(
                                "Reply blocked by safety filter for comment by %s",
                                comment_data["author"],
                            )
                            continue

                        if dry_run:
                            logger.info(
                                "[DRY RUN] Would reply to %s: %s",
                                comment_data["author"],
                                reply_text[:80],
                            )
                        else:
                            success = await _post_reply(page, reply_text)
                            if not success:
                                continue

                        # Track
                        replied_set.add(comment_key)
                        remaining -= 1

                        result = {
                            "commenter": comment_data["author"],
                            "comment": comment_data["text"][:200],
                            "reply": reply_text,
                            "post_author": post["author"],
                            "timestamp": datetime.utcnow().isoformat(),
                            "dry_run": dry_run,
                        }
                        results.append(result)

                        log_reply(
                            persona="MainUser",
                            commenter=comment_data["author"],
                            original_post_url="activity",
                            comment_text=comment_data["text"],
                            reply_text=reply_text,
                        )

                        if sheets_client:
                            sheets_client.log(
                                "REPLY",
                                "MainUser",
                                comment_data["author"],
                                "DRY_RUN" if dry_run else "OK",
                            )

                        # Lead check
                        lead = evaluate_lead(
                            name=comment_data["author"],
                            comment_text=comment_data["text"],
                            interaction_type="comment",
                        )
                        if lead:
                            add_lead(lead)

                        # Delay between replies
                        await asyncio.sleep(random.randint(60, 180))

            except Exception as e:
                logger.error("Error processing post %d: %s", post["element_index"], e)
                continue

    # Save tracker
    tracker["replied_to"] = list(replied_set)
    tracker["last_run"] = datetime.utcnow().isoformat()
    _save_reply_tracker(tracker)

    return results


def _check_reply_rules(comment_text: str, rules: list) -> str:
    """Check a comment against reply rules.

    Uses the sheet's ReplyRules tab (columns: ConditionType, Trigger,
    Action, Notes). ConditionType is "Forbidden" or "Allowed".

    Returns: "REPLY", "BLOCK", or "IGNORE".
    """
    comment_lower = comment_text.lower()

    for rule in rules:
        if rule.trigger.lower() in comment_lower:
            return rule.action.value

    # Default: reply to comments that seem substantive
    word_count = len(comment_text.split())
    if word_count < 3:
        return "IGNORE"  # Skip very short comments like "nice" or emojis

    return "REPLY"


def _generate_reply(
    comment_text: str,
    original_post: str,
    persona: dict,
) -> Optional[str]:
    """Generate a contextual reply using the LLM provider (Claude -> OpenAI).

    This is a synchronous function because the LLM provider calls are synchronous.
    """
    return llm_generate_reply(
        comment_text=comment_text,
        original_post=original_post,
        persona_system_prompt=persona.get("system_prompt", ""),
    )


async def _post_reply(page, reply_text: str) -> bool:
    """Post a reply in the currently open comment thread."""
    try:
        from browser.human_typing import human_type_into_element

        # Find the reply input — last visible textbox on the page
        reply_boxes = page.locator("div[role='textbox']")
        count = await reply_boxes.count()
        if count == 0:
            logger.error("No reply textbox found")
            return False

        reply_box = reply_boxes.last
        await human_type_into_element(page, reply_box, reply_text)
        await asyncio.sleep(random.uniform(0.5, 1.0))

        # Submit — look for a Post/Submit button
        submit = page.locator("button").filter(has_text="Post").last
        if await submit.count() > 0:
            await submit.click()
        else:
            submit = page.locator("button[aria-label*='Post'], button[aria-label*='Submit']")
            if await submit.count() > 0:
                await submit.last.click()
            else:
                await page.keyboard.press("Control+Enter")

        await asyncio.sleep(random.uniform(2.0, 4.0))
        return True

    except Exception as e:
        logger.error("Failed to post reply: %s", e)
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_replier(dry_run=True))
