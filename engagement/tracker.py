"""
Daily activity tracking (local secondary log).

Creates daily markdown files in tracking/linkedin/YYYY-MM-DD.md
to record all actions taken. Pattern ported from auto-commenter.

NOTE: The Google Sheet SystemLog is the primary source of truth for all
activity tracking. This local tracker exists as a secondary log for
quick offline review and debugging. If there's ever a discrepancy,
the Sheet data wins.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from utils import project_path

logger = logging.getLogger(__name__)

TRACKING_DIR = project_path("tracking", "linkedin")


def _today_file() -> str:
    return os.path.join(TRACKING_DIR, f"{datetime.now().strftime('%Y-%m-%d')}.md")


def _ensure_dir():
    Path(TRACKING_DIR).mkdir(parents=True, exist_ok=True)


def get_daily_stats(persona: Optional[str] = None) -> dict:
    """Read today's tracking file and return stats.

    Args:
        persona: If provided, only count actions by this persona.
                 If None, counts all actions (original behavior).

    Returns dict with keys: comments_posted, posts_made, replies_sent,
    likes_given, last_action_time, actions (list).
    """
    path = _today_file()
    stats = {
        "comments_posted": 0,
        "posts_made": 0,
        "replies_sent": 0,
        "likes_given": 0,
        "last_action_time": None,
        "actions": [],
        "commented_urls": set(),
    }

    if not os.path.exists(path):
        return stats

    with open(path, "r") as f:
        content = f.read()

    if persona is None:
        # Original behavior: read summary counters
        for line in content.split("\n"):
            if line.startswith("- **Comments posted**:"):
                stats["comments_posted"] = _parse_int(line)
            elif line.startswith("- **Posts made**:"):
                stats["posts_made"] = _parse_int(line)
            elif line.startswith("- **Replies sent**:"):
                stats["replies_sent"] = _parse_int(line)
            elif line.startswith("- **Likes given**:"):
                stats["likes_given"] = _parse_int(line)
            elif line.startswith("- **Last action**:"):
                stats["last_action_time"] = line.split(":", 1)[-1].strip()
    else:
        # Per-persona: parse individual entries and count by persona
        import re
        # Split into entries by ### headers
        entries = re.split(r'\n### ', content)
        for entry in entries:
            if f"**Persona**: {persona}" not in entry:
                continue
            if "Comment on post by" in entry or "Comment" in entry.split("\n")[0]:
                stats["comments_posted"] += 1
            elif "Post by" in entry:
                stats["posts_made"] += 1
            elif "Reply to" in entry:
                stats["replies_sent"] += 1
            elif "Like by" in entry:
                stats["likes_given"] += 1

    # Extract URLs that have been commented on
    import re
    urls = re.findall(r'\*\*Post\*\*:.*?\((https?://[^\)]+)\)', content)
    stats["commented_urls"] = set(urls)

    return stats


def log_comment(
    persona: str,
    author: str,
    post_url: str,
    post_summary: str,
    comment_text: str,
    comment_url: Optional[str] = None,
) -> None:
    """Log a comment action to today's tracking file."""
    _ensure_dir()
    path = _today_file()
    now = datetime.now()
    time_str = now.strftime("%H:%M")

    entry = f"""
### [{time_str}] Comment on post by {author}
- **Persona**: {persona}
- **Post**: [{post_summary[:60]}...]({post_url})
- **Author**: {author}
- **Comment Link**: {comment_url or 'N/A'}
- **Comment Content**:
```
{comment_text}
```
"""
    _append_entry(path, entry, "comments_posted")


def log_post(
    persona: str,
    post_content: str,
    post_url: Optional[str] = None,
    queue_id: str = "",
) -> None:
    """Log a post action to today's tracking file."""
    _ensure_dir()
    path = _today_file()
    now = datetime.now()
    time_str = now.strftime("%H:%M")

    preview = post_content[:100].replace("\n", " ")
    entry = f"""
### [{time_str}] Post by {persona}
- **Queue ID**: {queue_id}
- **URL**: {post_url or 'pending'}
- **Content Preview**: {preview}...
"""
    _append_entry(path, entry, "posts_made")


def log_reply(
    persona: str,
    commenter: str,
    original_post_url: str,
    comment_text: str,
    reply_text: str,
) -> None:
    """Log a reply action to today's tracking file."""
    _ensure_dir()
    path = _today_file()
    now = datetime.now()
    time_str = now.strftime("%H:%M")

    entry = f"""
### [{time_str}] Reply to {commenter}
- **Persona**: {persona}
- **Post**: {original_post_url}
- **Their comment**: {comment_text[:80]}...
- **Our reply**:
```
{reply_text}
```
"""
    _append_entry(path, entry, "replies_sent")


def log_like(persona: str, post_url: str, author: str) -> None:
    """Log a like action."""
    _ensure_dir()
    path = _today_file()
    now = datetime.now()
    time_str = now.strftime("%H:%M")

    entry = f"\n### [{time_str}] Like by {persona} on post by {author}\n- **URL**: {post_url}\n"
    _append_entry(path, entry, "likes_given")


def _append_entry(path: str, entry: str, counter_key: str) -> None:
    """Append an entry to the tracking file and update counters."""
    now = datetime.now()

    if not os.path.exists(path):
        # Create the file with header
        header = f"""# LinkedIn Activity - {now.strftime('%Y-%m-%d')}

## Daily Stats
- **Comments posted**: 0
- **Posts made**: 0
- **Replies sent**: 0
- **Likes given**: 0
- **Last action**: {now.strftime('%H:%M')}

---

## Activity Log
"""
        with open(path, "w") as f:
            f.write(header)

    # Append the entry
    with open(path, "a") as f:
        f.write(entry)

    # Update the counter in the stats section
    _update_counter(path, counter_key)
    _update_last_action(path, now.strftime("%H:%M"))


def _update_counter(path: str, key: str) -> None:
    """Increment a counter in the stats section."""
    key_map = {
        "comments_posted": "Comments posted",
        "posts_made": "Posts made",
        "replies_sent": "Replies sent",
        "likes_given": "Likes given",
    }
    display_key = key_map.get(key, key)

    with open(path, "r") as f:
        content = f.read()

    import re
    pattern = rf"(\*\*{display_key}\*\*: )(\d+)"
    match = re.search(pattern, content)
    if match:
        current = int(match.group(2))
        content = content[:match.start(2)] + str(current + 1) + content[match.end(2):]
        with open(path, "w") as f:
            f.write(content)


def _update_last_action(path: str, time_str: str) -> None:
    """Update the last action timestamp."""
    with open(path, "r") as f:
        content = f.read()

    import re
    content = re.sub(
        r"\*\*Last action\*\*: .*",
        f"**Last action**: {time_str}",
        content,
    )
    with open(path, "w") as f:
        f.write(content)


def _parse_int(line: str) -> int:
    """Extract an integer from a stats line."""
    import re
    match = re.search(r"(\d+)", line.split(":")[-1])
    return int(match.group(1)) if match else 0
