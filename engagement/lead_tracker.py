"""
Lead identification and logging.

Flags LinkedIn users who show interest (comments on our posts,
engages repeatedly, has relevant title/company). Ported from
auto-commenter lead identification patterns.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

LEADS_FILE = "tracking/linkedin/leads.json"

# Job titles that indicate a potential lead
LEAD_TITLES = [
    "cto", "cio", "vp engineering", "vp operations",
    "director of operations", "head of automation",
    "chief technology", "chief operating",
    "supply chain director", "supply chain manager",
    "operations manager", "process improvement",
    "digital transformation", "innovation",
    "head of ai", "ai lead", "ml engineer",
    "data science lead", "engineering manager",
    "founder", "co-founder", "ceo",
]

# Keywords in posts/comments that signal interest
INTEREST_SIGNALS = [
    "automation", "interested in your approach",
    "how did you", "can you share more",
    "would love to learn", "what tools",
    "we're looking for", "similar challenge",
    "dm me", "let's connect", "great insight",
]


def _ensure_file():
    Path(os.path.dirname(LEADS_FILE)).mkdir(parents=True, exist_ok=True)
    if not os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, "w") as f:
            json.dump({"leads": [], "updated": datetime.utcnow().isoformat()}, f, indent=2)


def load_leads() -> list[dict]:
    """Load the current leads list."""
    _ensure_file()
    with open(LEADS_FILE, "r") as f:
        data = json.load(f)
    return data.get("leads", [])


def save_leads(leads: list[dict]) -> None:
    """Save the leads list."""
    _ensure_file()
    with open(LEADS_FILE, "w") as f:
        json.dump(
            {"leads": leads, "updated": datetime.utcnow().isoformat()},
            f,
            indent=2,
        )


def evaluate_lead(
    name: str,
    title: str = "",
    company: str = "",
    comment_text: str = "",
    post_url: str = "",
    interaction_type: str = "comment",
) -> Optional[dict]:
    """Evaluate whether a user interaction indicates a potential lead.

    Returns a lead dict if the person qualifies, None otherwise.
    """
    score = 0
    reasons = []

    # Check title relevance
    title_lower = title.lower()
    for lead_title in LEAD_TITLES:
        if lead_title in title_lower:
            score += 30
            reasons.append(f"Relevant title: {title}")
            break

    # Check comment for interest signals
    comment_lower = comment_text.lower()
    for signal in INTEREST_SIGNALS:
        if signal in comment_lower:
            score += 20
            reasons.append(f"Interest signal: '{signal}'")
            break

    # Engagement type bonus
    if interaction_type == "comment":
        score += 10
    elif interaction_type == "share":
        score += 15

    # Only flag as lead if score is meaningful
    if score < 30:
        return None

    lead = {
        "name": name,
        "title": title,
        "company": company,
        "score": score,
        "reasons": reasons,
        "source_url": post_url,
        "interaction_type": interaction_type,
        "comment_preview": comment_text[:200] if comment_text else "",
        "discovered_at": datetime.utcnow().isoformat(),
        "status": "new",
    }

    logger.info("Potential lead identified: %s (%s) - score: %d", name, title, score)
    return lead


def add_lead(lead: dict) -> bool:
    """Add a lead if not already tracked. Returns True if new."""
    leads = load_leads()

    # Check for duplicates by name + company
    for existing in leads:
        if existing["name"] == lead["name"] and existing.get("company") == lead.get("company"):
            # Update interaction count
            existing.setdefault("interaction_count", 1)
            existing["interaction_count"] += 1
            existing["last_seen"] = datetime.utcnow().isoformat()
            save_leads(leads)
            logger.info("Updated existing lead: %s (interactions: %d)",
                        lead["name"], existing["interaction_count"])
            return False

    leads.append(lead)
    save_leads(leads)
    logger.info("New lead added: %s", lead["name"])
    return True
