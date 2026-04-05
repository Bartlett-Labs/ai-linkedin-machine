"""
LinkedIn DM auto-responder — intelligent intent-based replies to incoming messages.

Scans the messaging inbox for unread conversations, classifies intent using
the LLM (greeting, job opportunity, business inquiry, collaboration, question,
compliment, sales pitch, spam, follow-up), generates an appropriate response
per category, and sends replies with a 15-45 minute random delay for natural pacing.

All replies go through the safety filter. Spam messages are ignored entirely.
"""

import asyncio
import hashlib
import json
import logging
import os
import random
from datetime import datetime, date, timedelta
from typing import Optional

from browser.context_manager import PersonaContext
from browser.linkedin_actions import (
    get_unread_conversations,
    read_conversation_messages,
    send_dm_reply,
    mark_conversation_read,
    LinkedInChallengeDetected,
)
from config import load_personas
from llm.provider import classify_dm_intent, generate_dm_reply
from summarization.safety_filter import violates_safety
from utils import project_path
from utils.kill_switch import check_kill_switch, activate_kill_switch

logger = logging.getLogger(__name__)

TRACKER_PATH = project_path("tracking", "linkedin", "dm_replies.json")

# Configuration
MAX_REPLIES_PER_DAY = 20
REPLY_DELAY_MIN_MINUTES = 15
REPLY_DELAY_MAX_MINUTES = 45


def _load_tracker() -> dict:
    if os.path.exists(TRACKER_PATH):
        with open(TRACKER_PATH, "r") as f:
            return json.load(f)
    return {
        "replied_to": [],
        "reply_queue": [],
        "replies_sent": [],
        "daily_counts": {},
    }


def _save_tracker(tracker: dict) -> None:
    os.makedirs(os.path.dirname(TRACKER_PATH), exist_ok=True)
    with open(TRACKER_PATH, "w") as f:
        json.dump(tracker, f, indent=2)


def _get_today_count(tracker: dict) -> int:
    today = date.today().isoformat()
    return tracker.get("daily_counts", {}).get(today, 0)


def _increment_today(tracker: dict) -> None:
    today = date.today().isoformat()
    if "daily_counts" not in tracker:
        tracker["daily_counts"] = {}
    tracker["daily_counts"][today] = tracker["daily_counts"].get(today, 0) + 1


def _make_dedup_key(sender: str, last_message_text: str) -> str:
    """Create a dedup key from sender name + hash of last message."""
    msg_hash = hashlib.md5(last_message_text.encode()).hexdigest()[:12]
    return f"{sender.lower().strip()}:{msg_hash}"


async def run_dm_responder(
    headless: bool = True,
    dry_run: bool = False,
    max_replies: int = 0,
) -> dict:
    """Run the DM auto-responder.

    Two-phase approach:
    1. Scan inbox for unread messages, classify intent, generate replies,
       queue with a 15-45 min delay.
    2. Process the queue — send any replies whose delay has elapsed.

    Args:
        headless: Run browser headless.
        dry_run: Classify and generate but don't send.
        max_replies: Override daily limit (0 = use default).

    Returns:
        Summary dict.
    """
    tracker = _load_tracker()
    daily_limit = max_replies or MAX_REPLIES_PER_DAY
    sent_today = _get_today_count(tracker)
    remaining = daily_limit - sent_today

    summary = {
        "conversations_scanned": 0,
        "intents": {},
        "replies_queued": 0,
        "replies_sent": 0,
        "spam_skipped": 0,
        "already_replied": 0,
        "safety_blocked": 0,
        "errors": [],
        "daily_total": sent_today,
        "daily_limit": daily_limit,
        "dry_run": dry_run,
    }

    if remaining <= 0 and not dry_run:
        logger.info("Daily DM reply limit reached (%d/%d)", sent_today, daily_limit)
        return summary

    # Load MainUser persona
    personas = load_personas()
    main_user = next((p for p in personas if p["name"] == "MainUser"), personas[0])
    replied_set = set(tracker.get("replied_to", []))

    async with PersonaContext("MainUser", headless=headless) as ctx:
        page = await ctx.new_page()

        # --- Phase 1: Scan inbox, classify, generate, queue ---
        try:
            conversations = await get_unread_conversations(page, max_conversations=15)
        except LinkedInChallengeDetected as e:
            logger.error("Challenge on messaging inbox: %s", e)
            activate_kill_switch(f"LinkedIn challenge in DM responder: {e}")
            summary["errors"].append(f"Challenge: {e}")
            return summary

        # Filter to unread only
        unread = [c for c in conversations if c.get("unread", False)]
        summary["conversations_scanned"] = len(unread)
        logger.info("Found %d unread conversations (of %d total)", len(unread), len(conversations))

        queued_this_run = 0

        for conv in unread:
            if check_kill_switch():
                break
            if queued_this_run + sent_today >= daily_limit and not dry_run:
                break

            sender = conv.get("sender", "Unknown")
            thread_index = conv.get("thread_index", 0)

            try:
                # Read conversation messages
                messages = await read_conversation_messages(page, thread_index, max_messages=10)
                if not messages:
                    logger.debug("No messages readable in conversation with %s", sender)
                    continue

                # Get the last non-self message for dedup
                incoming_msgs = [m for m in messages if not m.get("is_self", False)]
                if not incoming_msgs:
                    # All messages are from us — no new inbound to reply to
                    continue

                last_incoming = incoming_msgs[-1]
                dedup_key = _make_dedup_key(sender, last_incoming.get("text", ""))

                if dedup_key in replied_set:
                    summary["already_replied"] += 1
                    continue

                # Check if the last message in the thread is from us (we already replied)
                if messages[-1].get("is_self", False):
                    summary["already_replied"] += 1
                    replied_set.add(dedup_key)
                    continue

                # Build sender info for classification
                sender_info = {
                    "sender": sender,
                    "name": sender,
                    "headline": conv.get("headline", ""),
                    "profile_url": conv.get("profile_url", ""),
                }

                # Classify intent
                intent = classify_dm_intent(messages, sender_info)
                summary["intents"][intent] = summary["intents"].get(intent, 0) + 1
                logger.info("Conversation with %s classified as: %s", sender, intent)

                # Skip spam
                if intent == "spam":
                    summary["spam_skipped"] += 1
                    # Mark as read
                    if not dry_run:
                        await mark_conversation_read(page)
                        replied_set.add(dedup_key)
                    logger.info("Skipping spam from %s", sender)
                    continue

                # Generate reply
                reply_text = generate_dm_reply(
                    messages=messages,
                    sender_info=sender_info,
                    intent=intent,
                    persona_system_prompt=main_user.get("system_prompt", ""),
                )

                if not reply_text:
                    logger.warning("Failed to generate DM reply for %s (intent=%s)", sender, intent)
                    summary["errors"].append(f"Generation failed: {sender}")
                    continue

                # Safety check
                if violates_safety(reply_text):
                    logger.warning("DM reply for %s blocked by safety filter", sender)
                    summary["safety_blocked"] += 1
                    continue

                # Calculate send time (15-45 min delay)
                delay_minutes = random.randint(REPLY_DELAY_MIN_MINUTES, REPLY_DELAY_MAX_MINUTES)
                send_at = (datetime.utcnow() + timedelta(minutes=delay_minutes)).isoformat()

                queue_entry = {
                    "sender": sender,
                    "profile_url": conv.get("profile_url", ""),
                    "thread_index": thread_index,
                    "intent": intent,
                    "reply_text": reply_text,
                    "last_incoming_text": last_incoming.get("text", "")[:200],
                    "queued_at": datetime.utcnow().isoformat(),
                    "send_at": send_at,
                    "sent": False,
                    "dedup_key": dedup_key,
                }

                if dry_run:
                    logger.info(
                        "[DRY RUN] Would queue reply to %s (intent=%s, delay=%dm): %s",
                        sender, intent, delay_minutes, reply_text[:100],
                    )
                else:
                    tracker["reply_queue"].append(queue_entry)

                queued_this_run += 1
                summary["replies_queued"] += 1

                # Small delay between processing conversations
                await _random_pause(1.0, 3.0)

            except LinkedInChallengeDetected as e:
                logger.error("Challenge during DM processing: %s", e)
                activate_kill_switch(f"LinkedIn challenge in DM responder: {e}")
                summary["errors"].append(f"Challenge: {e}")
                break
            except Exception as e:
                logger.error("Error processing conversation with %s: %s", sender, e)
                summary["errors"].append(f"Error ({sender}): {e}")
                continue

        # Navigate back to inbox for Phase 2
        if not dry_run:
            # --- Phase 2: Process reply queue (send delayed replies) ---
            sent = await _process_reply_queue(page, tracker, dry_run=False)
            summary["replies_sent"] = sent

    # Persist tracker
    if not dry_run:
        tracker["replied_to"] = list(replied_set)
        _save_tracker(tracker)

    summary["daily_total"] = _get_today_count(tracker)
    logger.info("DM responder complete: %s", summary)
    return summary


async def _process_reply_queue(page, tracker: dict, dry_run: bool) -> int:
    """Send queued replies whose delay has elapsed.

    Returns number of replies actually sent.
    """
    sent = 0
    now = datetime.utcnow()
    queue = tracker.get("reply_queue", [])
    still_pending = []

    for entry in queue:
        if entry.get("sent", False):
            continue

        send_at_str = entry.get("send_at", "")
        try:
            send_at = datetime.fromisoformat(send_at_str)
        except (ValueError, TypeError):
            still_pending.append(entry)
            continue

        if now < send_at:
            # Not time yet
            still_pending.append(entry)
            continue

        if check_kill_switch():
            still_pending.append(entry)
            break

        sender = entry.get("sender", "Unknown")
        reply_text = entry.get("reply_text", "")
        thread_index = entry.get("thread_index", 0)

        if dry_run:
            logger.info("[DRY RUN] Would send queued reply to %s: %s", sender, reply_text[:80])
            sent += 1
            continue

        try:
            # Navigate back to inbox and open the right conversation
            from browser.linkedin_actions import (
                LINKEDIN_MESSAGING_INBOX_URL,
                read_conversation_messages,
            )
            await page.goto(LINKEDIN_MESSAGING_INBOX_URL, wait_until="domcontentloaded")
            await _random_pause(2.0, 4.0)

            # Re-read messages to verify conversation is still in same state
            messages = await read_conversation_messages(page, thread_index, max_messages=3)

            # Send the reply
            success = await send_dm_reply(page, reply_text)
            if success:
                entry["sent"] = True
                entry["sent_at"] = now.isoformat()

                # Move to replies_sent
                if "replies_sent" not in tracker:
                    tracker["replies_sent"] = []
                tracker["replies_sent"].append({
                    "sender": sender,
                    "intent": entry.get("intent", ""),
                    "reply_text": reply_text,
                    "sent_at": now.isoformat(),
                })

                # Add dedup key
                dedup_key = entry.get("dedup_key", "")
                if dedup_key:
                    replied_set = set(tracker.get("replied_to", []))
                    replied_set.add(dedup_key)
                    tracker["replied_to"] = list(replied_set)

                _increment_today(tracker)
                sent += 1
                logger.info("Sent queued DM reply to %s (intent=%s)", sender, entry.get("intent"))

                # Delay between sends
                await _random_pause(30, 90)
            else:
                logger.error("Failed to send queued reply to %s", sender)
                still_pending.append(entry)

        except LinkedInChallengeDetected as e:
            logger.error("Challenge during queued reply send: %s", e)
            activate_kill_switch(f"LinkedIn challenge in DM queue: {e}")
            still_pending.append(entry)
            break
        except Exception as e:
            logger.error("Error sending queued reply to %s: %s", sender, e)
            still_pending.append(entry)

    tracker["reply_queue"] = still_pending
    return sent


async def get_dm_responder_status() -> dict:
    """Get current DM responder status for API/dashboard."""
    tracker = _load_tracker()
    today = date.today().isoformat()

    replied_today = tracker.get("daily_counts", {}).get(today, 0)
    queue = [e for e in tracker.get("reply_queue", []) if not e.get("sent", False)]
    recent_sent = tracker.get("replies_sent", [])[-20:]

    # Intent breakdown from recent sends
    intent_counts = {}
    for r in tracker.get("replies_sent", []):
        intent = r.get("intent", "unknown")
        intent_counts[intent] = intent_counts.get(intent, 0) + 1

    return {
        "replied_today": replied_today,
        "daily_limit": MAX_REPLIES_PER_DAY,
        "queue_depth": len(queue),
        "queue": queue,
        "total_replied": len(tracker.get("replies_sent", [])),
        "recent_replies": recent_sent,
        "intent_breakdown": intent_counts,
    }


async def _random_pause(min_sec: float, max_sec: float) -> None:
    await asyncio.sleep(random.uniform(min_sec, max_sec))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LinkedIn DM Auto-Responder")
    parser.add_argument("--dry-run", action="store_true", help="Classify and generate without sending")
    parser.add_argument("--max", type=int, default=0, help="Override daily reply limit")
    parser.add_argument("--no-headless", action="store_true", help="Show browser window")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    result = asyncio.run(
        run_dm_responder(
            headless=not args.no_headless,
            dry_run=args.dry_run,
            max_replies=args.max,
        )
    )
    print(json.dumps(result, indent=2))
