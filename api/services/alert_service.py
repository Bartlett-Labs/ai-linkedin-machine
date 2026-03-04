"""Engagement alert service — tracks unresponded comments with countdown timers."""

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from utils import project_path

logger = logging.getLogger(__name__)

REPLY_TRACKER_PATH = project_path("queue", "engagement", "reply_tracker.json")

# Urgency thresholds in minutes
URGENCY_THRESHOLDS = {
    "optimal": 20,
    "good": 45,
    "urgent": 60,
    "missed": float("inf"),
}


@dataclass
class EngagementAlert:
    alert_id: str
    commenter_name: str
    commenter_url: str = ""
    comment_text: str = ""
    post_url: str = ""
    post_title: str = ""
    discovered_at: str = ""
    responded: bool = False
    dismissed: bool = False

    @property
    def elapsed_minutes(self) -> float:
        if not self.discovered_at:
            return 0
        try:
            discovered = datetime.fromisoformat(self.discovered_at)
            if discovered.tzinfo is None:
                discovered = discovered.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - discovered
            return delta.total_seconds() / 60
        except (ValueError, TypeError):
            return 0

    @property
    def urgency(self) -> str:
        elapsed = self.elapsed_minutes
        if elapsed < URGENCY_THRESHOLDS["optimal"]:
            return "optimal"
        if elapsed < URGENCY_THRESHOLDS["good"]:
            return "good"
        if elapsed < URGENCY_THRESHOLDS["urgent"]:
            return "urgent"
        return "missed"


class AlertManager:
    """Manages engagement alerts from multiple sources."""

    def __init__(self):
        self._alerts: dict[str, EngagementAlert] = {}
        self._load_from_reply_tracker()

    def _load_from_reply_tracker(self):
        """Load unresponded items from the reply tracker JSON."""
        if not os.path.exists(REPLY_TRACKER_PATH):
            return
        try:
            with open(REPLY_TRACKER_PATH, "r") as f:
                data = json.load(f)
            replied_to = set(data.get("replied_to", []))
            # Future: populate alerts from SystemLog comments that aren't in replied_to
        except Exception as e:
            logger.warning("Could not load reply tracker: %s", e)

    def add_alert(
        self,
        commenter_name: str,
        comment_text: str,
        post_url: str,
        post_title: str = "",
        commenter_url: str = "",
    ) -> EngagementAlert:
        """Add a new engagement alert."""
        alert_id = hashlib.md5(
            f"{commenter_name}:{post_url}:{comment_text[:50]}".encode()
        ).hexdigest()[:12]

        if alert_id in self._alerts:
            return self._alerts[alert_id]

        alert = EngagementAlert(
            alert_id=alert_id,
            commenter_name=commenter_name,
            commenter_url=commenter_url,
            comment_text=comment_text,
            post_url=post_url,
            post_title=post_title,
            discovered_at=datetime.now(timezone.utc).isoformat(),
        )
        self._alerts[alert_id] = alert
        logger.info("New alert: %s from %s", alert_id, commenter_name)
        return alert

    def get_alerts(
        self,
        limit: int = 20,
        unresponded_only: bool = True,
    ) -> list[EngagementAlert]:
        """Get alerts sorted by urgency (most urgent first)."""
        alerts = list(self._alerts.values())
        if unresponded_only:
            alerts = [a for a in alerts if not a.responded and not a.dismissed]

        # Sort by elapsed time descending (most urgent first)
        alerts.sort(key=lambda a: a.elapsed_minutes, reverse=True)
        return alerts[:limit]

    def mark_responded(self, alert_id: str) -> None:
        if alert_id in self._alerts:
            self._alerts[alert_id].responded = True

    def dismiss(self, alert_id: str) -> None:
        if alert_id in self._alerts:
            self._alerts[alert_id].dismissed = True

    def ingest_from_system_log(self, log_entries: list[dict]) -> int:
        """Scan SystemLog entries for comments on our posts that need replies.

        Returns count of new alerts created.
        """
        count = 0
        for entry in log_entries:
            action = entry.get("Action", "").upper()
            if "COMMENT" not in action and "REPLY" not in action:
                continue
            # Only look for inbound comments (not our outbound ones)
            module = entry.get("Module", "")
            if module in ("Commenter", "Replier"):
                continue
            # This would be an inbound comment — create alert
            alert = self.add_alert(
                commenter_name=entry.get("Target", "Unknown"),
                comment_text=entry.get("Notes", ""),
                post_url=entry.get("Target", ""),
                post_title="",
            )
            if alert:
                count += 1
        return count
