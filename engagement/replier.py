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
from engagement.quality_checker import check_quality
from engagement.tracker import get_daily_stats, log_reply
from engagement.lead_tracker import evaluate_lead, add_lead
from llm.provider import generate_reply as llm_generate_reply
from summarization.safety_filter import violates_safety
from utils.kill_switch import check_kill_switch

logger = logging.getLogger(__name__)

PERSONAS_CONFIG = "config/personas.json"
TRACKER_FILE = "queue/engagement/reply_tracker.json"


def load_personas() -> list[dict]:
    with open(PERSONAS_CONFIG, "r") as f:
        return json.load(f)["personas"]


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
                post_elements = await page.query_selector_all("div.feed-shared-update-v2")
                if post["element_index"] < len(post_elements):
                    el = post_elements[post["element_index"]]
                    await el.scroll_into_view_if_needed()

                    # Click comment button to expand comments
                    comment_btn = await el.query_selector(
                        "button[aria-label*='Comment']"
                    )
                    if comment_btn:
                        await comment_btn.click()
                        await asyncio.sleep(random.uniform(1.5, 3.0))

                    comments = await get_post_comments(page)

                    for comment_data in comments:
                        comment_key = f"{post['urn']}:{comment_data['author']}"
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
                        reply_text = await _generate_reply(
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
                            "post_urn": post["urn"],
                            "timestamp": datetime.utcnow().isoformat(),
                            "dry_run": dry_run,
                        }
                        results.append(result)

                        log_reply(
                            persona="MainUser",
                            commenter=comment_data["author"],
                            original_post_url=post.get("urn", ""),
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
                logger.error("Error processing post %s: %s", post["urn"], e)
                continue

    # Save tracker
    tracker["replied_to"] = list(replied_set)
    tracker["last_run"] = datetime.utcnow().isoformat()
    _save_reply_tracker(tracker)

    return results


def _check_reply_rules(comment_text: str, rules: list) -> str:
    """Check a comment against reply rules.

    Returns: "REPLY", "BLOCK", or "IGNORE".
    """
    comment_lower = comment_text.lower()

    for rule in rules:
        if rule.trigger_phrase.lower() in comment_lower:
            return rule.action.value

    # Default: reply to comments that seem substantive
    word_count = len(comment_text.split())
    if word_count < 3:
        return "IGNORE"  # Skip very short comments like "nice" or emojis

    return "REPLY"


async def _generate_reply(
    comment_text: str,
    original_post: str,
    persona: dict,
) -> Optional[str]:
    """Generate a contextual reply using the LLM provider (Claude → OpenAI)."""
    return llm_generate_reply(
        comment_text=comment_text,
        original_post=original_post,
        persona_system_prompt=persona.get("system_prompt", ""),
    )


async def _post_reply(page, reply_text: str) -> bool:
    """Post a reply in the currently open comment thread."""
    try:
        # Find the reply input - it should be the last textbox visible
        reply_boxes = await page.query_selector_all("div.ql-editor[role='textbox']")
        if not reply_boxes:
            logger.error("No reply textbox found")
            return False

        reply_box = reply_boxes[-1]
        await reply_box.click()
        await asyncio.sleep(random.uniform(0.3, 0.6))

        # Type the reply
        for char in reply_text:
            await page.keyboard.type(char, delay=random.randint(50, 120))

        await asyncio.sleep(random.uniform(0.5, 1.0))

        # Submit
        submit_buttons = await page.query_selector_all(
            "button[aria-label*='Post comment'], button.comments-comment-box__submit-button"
        )
        if submit_buttons:
            await submit_buttons[-1].click()
            await asyncio.sleep(random.uniform(2.0, 4.0))
            return True

        logger.error("Submit button not found for reply")
        return False

    except Exception as e:
        logger.error("Failed to post reply: %s", e)
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_replier(dry_run=True))
