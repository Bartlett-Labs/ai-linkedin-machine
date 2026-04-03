"""
SQLAlchemy 2.0 models for the AI LinkedIn Machine.

Maps 1:1 from Google Sheet tabs to Postgres tables, plus 3 new tables
for pipeline tracking, feed sources, and pipeline triggers.

All models use the Mapped[] annotation style (SQLAlchemy 2.0).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# ---------------------------------------------------------------------------
# Enums (matching sheets/models.py)
# ---------------------------------------------------------------------------

import enum


class QueueStatusEnum(str, enum.Enum):
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class PhaseEnum(str, enum.Enum):
    STEALTH = "stealth"
    ANNOUNCEMENT = "announcement"
    AUTHORITY = "authority"


class EngineModeEnum(str, enum.Enum):
    LIVE = "Live"
    DRY_RUN = "DryRun"
    PAUSED = "Paused"


class ReplyActionEnum(str, enum.Enum):
    REPLY = "REPLY"
    BLOCK = "BLOCK"
    IGNORE = "IGNORE"


class PipelineStatusEnum(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# 1. SystemLog — append-only audit trail
# ---------------------------------------------------------------------------

class SystemLog(Base):
    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    module: Mapped[str] = mapped_column(String(100), default="", index=True)
    action: Mapped[str] = mapped_column(String(100), default="", index=True)
    target: Mapped[str] = mapped_column(String(500), default="")
    result: Mapped[str] = mapped_column(String(50), default="")
    safety: Mapped[str] = mapped_column(String(20), default="Safe")
    notes: Mapped[str] = mapped_column(Text, default="")


# ---------------------------------------------------------------------------
# 2. OutboundQueue — posts, comments, replies waiting to execute
# ---------------------------------------------------------------------------

class OutboundQueue(Base):
    __tablename__ = "outbound_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    post_id: Mapped[str] = mapped_column(String(100), default="")
    action_type: Mapped[str] = mapped_column(String(50), default="")
    persona: Mapped[str] = mapped_column(String(100), default="MainUser")
    target_name: Mapped[str] = mapped_column(String(200), default="")
    target_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    draft_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(
        String(20), default=QueueStatusEnum.READY.value, index=True
    )
    scheduled_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str] = mapped_column(Text, default="")

    __table_args__ = (
        Index("ix_outbound_queue_status_created", "status", "created_at"),
    )


# ---------------------------------------------------------------------------
# 3. EngineControl — singleton row controlling engine behavior
# ---------------------------------------------------------------------------

class EngineControl(Base):
    __tablename__ = "engine_control"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    mode: Mapped[str] = mapped_column(
        String(20), default=EngineModeEnum.DRY_RUN.value
    )
    phase: Mapped[str] = mapped_column(
        String(20), default=PhaseEnum.STEALTH.value
    )
    main_user_posting: Mapped[bool] = mapped_column(Boolean, default=True)
    phantom_engagement: Mapped[bool] = mapped_column(Boolean, default=True)
    commenting: Mapped[bool] = mapped_column(Boolean, default=True)
    replying: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)


# ---------------------------------------------------------------------------
# 4. ScheduleConfigs — per-phase rate limits
# ---------------------------------------------------------------------------

class ScheduleConfig(Base):
    __tablename__ = "schedule_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phase: Mapped[str] = mapped_column(String(30), unique=True)
    posts_per_week: Mapped[int] = mapped_column(Integer, default=3)
    comments_per_day_min: Mapped[int] = mapped_column(Integer, default=2)
    comments_per_day_max: Mapped[int] = mapped_column(Integer, default=5)
    phantom_comments_min: Mapped[int] = mapped_column(Integer, default=1)
    phantom_comments_max: Mapped[int] = mapped_column(Integer, default=3)
    min_delay_sec: Mapped[int] = mapped_column(Integer, default=30)
    max_likes_per_day: Mapped[int] = mapped_column(Integer, default=20)


# ---------------------------------------------------------------------------
# 5. SafetyTerms — blocked phrases
# ---------------------------------------------------------------------------

class SafetyTerm(Base):
    __tablename__ = "safety_terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    term: Mapped[str] = mapped_column(String(200), unique=True)
    response: Mapped[str] = mapped_column(String(20), default="BLOCK")


# ---------------------------------------------------------------------------
# 6. ReplyRules — what to do when someone comments on our posts
# ---------------------------------------------------------------------------

class ReplyRule(Base):
    __tablename__ = "reply_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    condition_type: Mapped[str] = mapped_column(String(30))
    trigger: Mapped[str] = mapped_column(String(500))
    action: Mapped[str] = mapped_column(String(20), default=ReplyActionEnum.REPLY.value)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# 7. CommentTemplates — fallback templates per persona
# ---------------------------------------------------------------------------

class CommentTemplate(Base):
    __tablename__ = "comment_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_text: Mapped[str] = mapped_column(Text)
    tone: Mapped[str] = mapped_column(String(50), default="")
    category: Mapped[str] = mapped_column(String(50), default="")
    safety_flag: Mapped[int] = mapped_column(Integer, default=0)
    example_use: Mapped[str] = mapped_column(Text, default="")
    persona: Mapped[str] = mapped_column(String(100), default="MainUser", index=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0)


# ---------------------------------------------------------------------------
# 8. CommentTargets — LinkedIn profiles to engage with
# ---------------------------------------------------------------------------

class CommentTarget(Base):
    __tablename__ = "comment_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    linkedin_url: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(50), default="network")
    priority: Mapped[int] = mapped_column(Integer, default=1)
    last_comment_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# 9. ContentBank — pre-written post drafts
# ---------------------------------------------------------------------------

class ContentBank(Base):
    __tablename__ = "content_bank"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(50), default="", index=True)
    post_type: Mapped[str] = mapped_column(String(30), default="")
    draft: Mapped[str] = mapped_column(Text, default="")
    safety_flag: Mapped[int] = mapped_column(Integer, default=0)
    ready: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# 10. RepostBank — curated articles for reposting
# ---------------------------------------------------------------------------

class RepostBank(Base):
    __tablename__ = "repost_bank"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(200), default="")
    source_url: Mapped[str] = mapped_column(String(500), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    commentary_prompt: Mapped[str] = mapped_column(Text, default="")
    safety_flag: Mapped[int] = mapped_column(Integer, default=0)
    last_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# 11. ActivityWindows — when the scheduler runs during the day
# ---------------------------------------------------------------------------

class ActivityWindow(Base):
    __tablename__ = "activity_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    window_name: Mapped[str] = mapped_column(String(100))
    start_hour: Mapped[int] = mapped_column(Integer, default=6)
    end_hour: Mapped[int] = mapped_column(Integer, default=8)
    days_of_week: Mapped[str] = mapped_column(String(50), default="all")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


# ---------------------------------------------------------------------------
# 12. FeedSources — RSS feeds to ingest (replaces config/feeds.json)
# ---------------------------------------------------------------------------

class FeedSource(Base):
    __tablename__ = "feed_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(500))
    feed_type: Mapped[str] = mapped_column(String(20), default="rss")
    category: Mapped[str] = mapped_column(String(50), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_fetched: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ---------------------------------------------------------------------------
# 13. PipelineRuns — execution history for the pipeline
# ---------------------------------------------------------------------------

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trigger_type: Mapped[str] = mapped_column(
        String(20), default="scheduled"
    )
    status: Mapped[str] = mapped_column(
        String(20), default=PipelineStatusEnum.RUNNING.value
    )
    phase: Mapped[str] = mapped_column(String(20), default="")
    posts_made: Mapped[int] = mapped_column(Integer, default=0)
    comments_made: Mapped[int] = mapped_column(Integer, default=0)
    replies_made: Mapped[int] = mapped_column(Integer, default=0)
    phantom_actions: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")


# ---------------------------------------------------------------------------
# 14. WebhookEvents — LinkedIn webhook notification log
# ---------------------------------------------------------------------------

class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(100), default="ORGANIZATION_SOCIAL_ACTION_NOTIFICATIONS"
    )
    action: Mapped[str] = mapped_column(String(50), default="", index=True)
    notification_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    organization_urn: Mapped[str] = mapped_column(String(200), default="")
    source_post_urn: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    generated_activity_urn: Mapped[str] = mapped_column(String(200), default="")
    actor_urn: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    comment_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    queue_item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
