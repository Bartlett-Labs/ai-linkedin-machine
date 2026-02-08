"""
Data models matching the Google Sheet schema.

The Sheet has 10 tabs: ContentBank, RepostBank, CommentTargets,
CommentTemplates, ReplyRules, SafetyTerms, ScheduleControl,
EngineControl, OutboundQueue, SystemLog.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class QueueStatus(str, Enum):
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class Phase(str, Enum):
    STEALTH = "stealth"
    ANNOUNCEMENT = "announcement"
    AUTHORITY = "authority"


class EngineMode(str, Enum):
    LIVE = "Live"
    DRY_RUN = "DryRun"
    PAUSED = "Paused"


class ReplyAction(str, Enum):
    REPLY = "REPLY"
    BLOCK = "BLOCK"
    IGNORE = "IGNORE"


@dataclass
class QueueItem:
    """Represents a row from the OutboundQueue tab."""
    row_index: int
    post_id: str
    persona: str
    content: str
    content_type: str  # "post", "comment", "reply"
    status: QueueStatus
    scheduled_time: Optional[str] = None
    target_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    executed_at: Optional[str] = None


@dataclass
class CommentTarget:
    """Represents a row from the CommentTargets tab."""
    name: str
    linkedin_url: str
    category: str  # "ai_leader", "ops_supply_chain", "network"
    priority: int = 1
    last_commented: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class CommentTemplate:
    """Represents a row from the CommentTemplates tab."""
    template_id: str
    category: str
    template_text: str
    persona: str = "MainUser"
    use_count: int = 0


@dataclass
class ReplyRule:
    """Represents a row from the ReplyRules tab."""
    trigger_phrase: str
    action: ReplyAction
    response_template: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class SafetyTerm:
    """Represents a row from the SafetyTerms tab."""
    term: str
    category: str  # "employer", "job_search", "self_promotion"
    severity: str = "BLOCK"  # "BLOCK" or "WARN"


@dataclass
class ScheduleWindow:
    """Represents a row from the ScheduleControl tab."""
    day_of_week: str
    window_name: str  # "morning" or "afternoon"
    start_time: str  # "08:00"
    end_time: str  # "11:00"
    enabled: bool = True


@dataclass
class EngineControl:
    """Represents the EngineControl tab settings."""
    mode: EngineMode = EngineMode.DRY_RUN
    phase: Phase = Phase.STEALTH
    main_user_posting: bool = True
    phantom_engagement: bool = True
    commenting: bool = True
    replying: bool = True
    last_run: Optional[str] = None


@dataclass
class SystemLogEntry:
    """A row to write to the SystemLog tab."""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    action: str = ""
    persona: str = ""
    target: str = ""
    status: str = ""
    details: str = ""
    error: Optional[str] = None
