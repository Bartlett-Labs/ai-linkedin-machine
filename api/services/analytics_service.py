"""Analytics service — aggregates data from tracker files and SystemLog."""

import os
import re
from collections import defaultdict
from datetime import datetime, timedelta

from engagement.tracker import get_daily_stats, TRACKING_DIR


def get_daily_summary(date_str: str = None) -> dict:
    """Get daily summary from the local tracker.

    If no date specified, returns today's stats.
    """
    stats = get_daily_stats()
    today = date_str or datetime.now().strftime("%Y-%m-%d")
    return {
        "date": today,
        "comments_posted": stats.get("comments_posted", 0),
        "posts_made": stats.get("posts_made", 0),
        "replies_sent": stats.get("replies_sent", 0),
        "likes_given": stats.get("likes_given", 0),
        "last_action_time": stats.get("last_action_time"),
    }


def get_engagement_trends(sheets, days: int = 30) -> list[dict]:
    """Get daily engagement counts from SystemLog over the last N days.

    Returns list of {date, comments, posts, replies, likes} dicts.
    """
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    entries, _ = sheets.get_system_log(limit=10000, offset=0, date_from=cutoff)

    # Aggregate by date
    daily = defaultdict(lambda: {"comments": 0, "posts": 0, "replies": 0, "likes": 0})

    for entry in entries:
        ts = entry.get("Timestamp", "")
        if not ts:
            continue
        date = ts[:10]  # YYYY-MM-DD
        action = entry.get("Action", "").upper()
        result = entry.get("Result", "").upper()

        # Only count successful actions
        if result in ("FAILED", "BLOCKED", "SKIPPED"):
            continue

        if "COMMENT" in action:
            daily[date]["comments"] += 1
        elif "POST" in action or "QUEUE" in action:
            daily[date]["posts"] += 1
        elif "REPLY" in action:
            daily[date]["replies"] += 1
        elif "LIKE" in action:
            daily[date]["likes"] += 1

    # Fill in missing dates with zeros
    result = []
    current = datetime.utcnow() - timedelta(days=days)
    for _ in range(days):
        date_str = current.strftime("%Y-%m-%d")
        counts = daily.get(date_str, {"comments": 0, "posts": 0, "replies": 0, "likes": 0})
        result.append({"date": date_str, **counts})
        current += timedelta(days=1)

    return result


def get_per_persona_stats(sheets, days: int = 30) -> list[dict]:
    """Get per-persona action counts from SystemLog.

    Persona is extracted from the Notes column (format: [PersonaName] ...).
    """
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    entries, _ = sheets.get_system_log(limit=10000, offset=0, date_from=cutoff)

    persona_counts = defaultdict(lambda: {"total_actions": 0, "comments": 0, "posts": 0, "replies": 0})

    for entry in entries:
        notes = entry.get("Notes", "")
        action = entry.get("Action", "").upper()
        result = entry.get("Result", "").upper()

        if result in ("FAILED", "BLOCKED", "SKIPPED"):
            continue

        # Extract persona from notes: "[PersonaName] ..."
        persona = "Unknown"
        match = re.match(r"\[([^\]]+)\]", notes)
        if match:
            persona = match.group(1)

        persona_counts[persona]["total_actions"] += 1
        if "COMMENT" in action:
            persona_counts[persona]["comments"] += 1
        elif "POST" in action:
            persona_counts[persona]["posts"] += 1
        elif "REPLY" in action:
            persona_counts[persona]["replies"] += 1

    return [
        {"persona": name, **counts}
        for name, counts in sorted(persona_counts.items())
    ]
