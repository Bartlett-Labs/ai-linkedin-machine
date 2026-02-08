"""
Weekly content planning and scheduling.

Determines which days get original posts vs engagement-only days,
rotates content streams, and manages morning vs afternoon posting windows.
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import yaml

logger = logging.getLogger(__name__)

TIMEZONE = ZoneInfo("America/Chicago")

# Content stream categories and rotation weights
CONTENT_STREAMS = {
    "ai_automation": {
        "weight": 0.35,
        "description": "AI tools, automation workflows, LLM applications",
    },
    "ops_efficiency": {
        "weight": 0.25,
        "description": "Operations, supply chain, process optimization",
    },
    "personal_growth": {
        "weight": 0.20,
        "description": "Builder mindset, learning in public, career growth",
    },
    "builder_stories": {
        "weight": 0.20,
        "description": "Bartlett Labs projects, tool reviews, behind-the-scenes",
    },
}

# Posting windows (US Central time)
POSTING_WINDOWS = {
    "morning": {"start": 7, "end": 10},
    "afternoon": {"start": 12, "end": 15},
}


def get_weekly_plan(
    phase: str = "stealth",
    schedule_windows: list = None,
) -> list[dict]:
    """Generate a weekly content plan.

    Args:
        phase: Current phase (stealth/announcement/authority).
        schedule_windows: Optional schedule windows from Sheet.

    Returns:
        List of daily plan dicts for the next 7 days.
    """
    now = datetime.now(TIMEZONE)
    plan = []

    if phase == "stealth":
        # 1-2 posts per week, rest is engagement-only
        post_days = _pick_post_days(now, posts_per_week=2)
    elif phase == "announcement":
        # 2 posts per day
        post_days = list(range(7))  # Every day
    else:  # authority
        post_days = list(range(7))

    # Rotate content streams across post days
    streams = list(CONTENT_STREAMS.keys())
    stream_index = now.isocalendar()[1] % len(streams)  # Rotate by week

    for day_offset in range(7):
        day = now + timedelta(days=day_offset)
        day_name = day.strftime("%A")
        is_post_day = day_offset in post_days

        daily_plan = {
            "date": day.strftime("%Y-%m-%d"),
            "day": day_name,
            "is_post_day": is_post_day,
            "actions": [],
        }

        if is_post_day:
            # Assign content stream
            stream = streams[stream_index % len(streams)]
            stream_index += 1

            # Pick posting window
            window = _pick_posting_window(day, schedule_windows)

            daily_plan["actions"].append({
                "type": "post",
                "content_stream": stream,
                "window": window,
                "persona": "MainUser",
            })

            if phase in ("announcement", "authority"):
                # Second post in afternoon window
                second_stream = streams[stream_index % len(streams)]
                stream_index += 1
                daily_plan["actions"].append({
                    "type": "post",
                    "content_stream": second_stream,
                    "window": "afternoon",
                    "persona": "MainUser",
                })

        # Engagement actions every day
        daily_plan["actions"].append({
            "type": "comment",
            "target_category": "ai_leaders",
            "count": _get_comment_count(phase, "ai_leaders"),
        })
        daily_plan["actions"].append({
            "type": "comment",
            "target_category": "ops_supply_chain",
            "count": _get_comment_count(phase, "ops_supply_chain"),
        })
        daily_plan["actions"].append({
            "type": "comment",
            "target_category": "network",
            "count": _get_comment_count(phase, "network"),
        })
        daily_plan["actions"].append({
            "type": "reply_check",
        })

        plan.append(daily_plan)

    return plan


def is_in_posting_window(
    schedule_windows: list = None,
) -> tuple[bool, str]:
    """Check if the current time is within a posting window.

    Returns:
        Tuple of (is_in_window, window_name).
    """
    now = datetime.now(TIMEZONE)
    hour = now.hour

    if schedule_windows:
        for window in schedule_windows:
            if not window.enabled:
                continue
            if window.day_of_week.lower() != now.strftime("%A").lower():
                continue
            start = int(window.start_time.split(":")[0])
            end = int(window.end_time.split(":")[0])
            if start <= hour < end:
                return True, window.window_name
        return False, ""

    # Default windows
    for name, times in POSTING_WINDOWS.items():
        if times["start"] <= hour < times["end"]:
            return True, name

    return False, ""


def get_next_posting_time(
    phase: str = "stealth",
    schedule_windows: list = None,
) -> Optional[datetime]:
    """Calculate the next posting time based on phase and schedule.

    Returns a datetime in US Central timezone.
    """
    now = datetime.now(TIMEZONE)

    if schedule_windows:
        for window in schedule_windows:
            if not window.enabled:
                continue
            start_hour = int(window.start_time.split(":")[0])
            end_hour = int(window.end_time.split(":")[0])

            # Random time within the window
            post_hour = random.randint(start_hour, end_hour - 1)
            post_minute = random.randint(0, 59)

            candidate = now.replace(
                hour=post_hour, minute=post_minute, second=0, microsecond=0
            )
            if candidate > now:
                return candidate

    # Default: pick a random time in the next available window
    for name, times in POSTING_WINDOWS.items():
        if now.hour < times["end"]:
            post_hour = max(now.hour + 1, times["start"])
            if post_hour < times["end"]:
                return now.replace(
                    hour=post_hour,
                    minute=random.randint(0, 59),
                    second=0,
                    microsecond=0,
                )

    # Tomorrow morning
    tomorrow = now + timedelta(days=1)
    morning = POSTING_WINDOWS["morning"]
    return tomorrow.replace(
        hour=random.randint(morning["start"], morning["end"] - 1),
        minute=random.randint(0, 59),
        second=0,
        microsecond=0,
    )


def _pick_post_days(now: datetime, posts_per_week: int) -> list[int]:
    """Pick which days of the week to post (0=today, 6=6 days from now).

    Spreads posts across the week, preferring Tue-Thu.
    """
    preferred = [1, 2, 3]  # Tue, Wed, Thu (offset from Monday)
    today_weekday = now.weekday()

    # Map preferred weekdays to day offsets from today
    candidates = []
    for day_offset in range(7):
        weekday = (today_weekday + day_offset) % 7
        if weekday in preferred:
            candidates.append(day_offset)

    if len(candidates) >= posts_per_week:
        return sorted(random.sample(candidates, posts_per_week))

    # Not enough preferred days, add more
    all_days = list(range(7))
    random.shuffle(all_days)
    while len(candidates) < posts_per_week and all_days:
        d = all_days.pop()
        if d not in candidates:
            candidates.append(d)

    return sorted(candidates[:posts_per_week])


def _pick_posting_window(
    day: datetime,
    schedule_windows: list = None,
) -> str:
    """Pick morning or afternoon window for a given day."""
    if schedule_windows:
        day_name = day.strftime("%A").lower()
        available = [
            w for w in schedule_windows
            if w.day_of_week.lower() == day_name and w.enabled
        ]
        if available:
            return random.choice(available).window_name

    return random.choice(["morning", "afternoon"])


def _get_comment_count(phase: str, category: str) -> int:
    """Get recommended comment count per category based on phase.

    MainUser targeting:
    - 5 AI/automation leaders
    - 2-4 ops/supply chain
    - 1-3 network
    """
    counts = {
        "stealth": {
            "ai_leaders": random.randint(3, 5),
            "ops_supply_chain": random.randint(2, 3),
            "network": random.randint(1, 2),
        },
        "announcement": {
            "ai_leaders": random.randint(5, 7),
            "ops_supply_chain": random.randint(3, 4),
            "network": random.randint(2, 3),
        },
        "authority": {
            "ai_leaders": 5,
            "ops_supply_chain": random.randint(3, 4),
            "network": random.randint(2, 3),
        },
    }
    return counts.get(phase, counts["stealth"]).get(category, 2)
