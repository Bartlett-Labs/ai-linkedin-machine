"""
Data models matching the Google Sheet schema.

The Sheet has 11 tabs: SystemLog, OutboundQueue, EngineControl, Credentials,
ScheduleControl, SafetyTerms, ReplyRules, CommentTemplates, CommentTargets,
RepostBank, ContentBank.

Each dataclass documents the exact sheet column names it maps to.
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

    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if member.value.lower() == str(value).lower():
                return member
        return None


class EngineMode(str, Enum):
    LIVE = "Live"
    DRY_RUN = "DryRun"
    PAUSED = "Paused"

    @classmethod
    def _missing_(cls, value):
        lookup = {"live": cls.LIVE, "dryrun": cls.DRY_RUN, "dry_run": cls.DRY_RUN,
                  "paused": cls.PAUSED}
        return lookup.get(str(value).lower().replace(" ", ""))


class ReplyAction(str, Enum):
    REPLY = "REPLY"
    BLOCK = "BLOCK"
    IGNORE = "IGNORE"


@dataclass
class QueueItem:
    """Represents a row from the OutboundQueue tab.

    Sheet columns: Timestamp, ActionType, TargetName, TargetURL,
                   DraftText, Status, Notes, ExecuteLink, CopyReady
    """
    row_index: int
    post_id: str
    persona: str
    content: str
    content_type: str  # "post", "COMMENT_DRAFT", "REPLY_DRAFT"
    status: QueueStatus
    scheduled_time: Optional[str] = None
    target_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    executed_at: Optional[str] = None


@dataclass
class CommentTarget:
    """Represents a row from the CommentTargets tab.

    Sheet columns: ID, Name, LinkedInURL, Category, Priority,
                   LastCommentDate, Notes
    """
    name: str
    linkedin_url: str
    category: str  # "ai_leader", "ops_supply_chain", "network"
    priority: int = 1
    last_comment_date: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class CommentTemplate:
    """Represents a row from the CommentTemplates tab.

    Sheet columns: ID, TemplateText, Tone, Category, SafetyFlag, ExampleUse
    """
    template_id: str
    template_text: str
    tone: str = ""
    category: str = ""
    safety_flag: int = 0
    example_use: str = ""
    persona: str = "MainUser"
    use_count: int = 0


@dataclass
class ReplyRule:
    """Represents a row from the ReplyRules tab.

    Sheet columns: ConditionType, Trigger, Action, Notes
    """
    condition_type: str  # "Forbidden" or "Allowed"
    trigger: str
    action: ReplyAction
    notes: Optional[str] = None


@dataclass
class SafetyTerm:
    """Represents a row from the SafetyTerms tab.

    Sheet columns: Term, Response
    """
    term: str
    response: str = "BLOCK"  # "BLOCK" or "MASK"


@dataclass
class ScheduleConfig:
    """Represents a row from the ScheduleControl tab.

    Sheet columns: Mode, PostsPerWeek, CommentsPerDay, PhantomComments,
                   MinDelaySec, MaxLikesPerDay

    Controls rate limits per phase. Overrides config/rate_limits.yaml
    when present. CommentsPerDay and PhantomComments may be ranges
    (e.g. "7-12").
    """
    mode: str  # "Stealth", "PostAnnouncement", "Authority"
    posts_per_week: int = 2
    comments_per_day_min: int = 7
    comments_per_day_max: int = 12
    phantom_comments_min: int = 1
    phantom_comments_max: int = 2
    min_delay_sec: int = 300
    max_likes_per_day: int = 20


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
    """A row to write to the SystemLog tab.

    Sheet columns: Timestamp, Module, Action, Target, Result, Safety, Notes
    """
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    module: str = ""
    action: str = ""
    target: str = ""
    result: str = ""
    safety: str = "Safe"
    notes: str = ""


@dataclass
class ContentBankItem:
    """Represents a row from the ContentBank tab.

    Sheet columns: ID, Category, PostType, Draft, SafetyFlag, Ready,
                   LastUsed, Notes
    """
    item_id: int = 0
    category: str = ""
    post_type: str = ""  # "Original", "Repost", "Build", "Workflow"
    draft: str = ""
    safety_flag: int = 0
    ready: bool = True
    last_used: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class RepostBankItem:
    """Represents a row from the RepostBank tab.

    Sheet columns: ID, SourceName, SourceURL, Summary, CommentaryPrompt,
                   SafetyFlag, LastUsed, Notes
    """
    item_id: int = 0
    source_name: str = ""
    source_url: str = ""
    summary: str = ""
    commentary_prompt: str = ""
    safety_flag: int = 0
    last_used: Optional[str] = None
    notes: Optional[str] = None
