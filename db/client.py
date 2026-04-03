"""
DatabaseClient — drop-in replacement for SheetsClient.

Every public method mirrors SheetsClient's signature and return type,
so consumer code (main.py, orchestrator, API routes) can swap imports
without any other changes.

Uses sync SQLAlchemy sessions (the pipeline is sync). For async FastAPI
routes, use the async session factory from db.engine directly.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import Session

from db.engine import sync_session, get_sync_session_factory
from db import models as m

# Re-export the dataclasses that consumers expect
from sheets.models import (
    QueueItem,
    QueueStatus,
    CommentTarget as CommentTargetDC,
    CommentTemplate as CommentTemplateDC,
    ReplyRule as ReplyRuleDC,
    ReplyAction,
    SafetyTerm as SafetyTermDC,
    ScheduleConfig as ScheduleConfigDC,
    EngineControl as EngineControlDC,
    EngineMode,
    Phase,
    SystemLogEntry,
    ContentBankItem,
    RepostBankItem,
    ActivityWindow as ActivityWindowDC,
)

logger = logging.getLogger(__name__)

# Tab name constants (mirrors sheets.client.TAB_* for import compatibility)
TAB_OUTBOUND_QUEUE = "OutboundQueue"
TAB_COMMENT_TARGETS = "CommentTargets"
TAB_COMMENT_TEMPLATES = "CommentTemplates"
TAB_REPLY_RULES = "ReplyRules"
TAB_SAFETY_TERMS = "SafetyTerms"
TAB_SCHEDULE_CONTROL = "ScheduleControl"
TAB_ENGINE_CONTROL = "EngineControl"
TAB_SYSTEM_LOG = "SystemLog"
TAB_CONTENT_BANK = "ContentBank"
TAB_REPOST_BANK = "RepostBank"
TAB_ACTIVITY_WINDOWS = "ActivityWindows"

# Map ScheduleControl "mode" column values to Phase enum values
_SCHEDULE_MODE_TO_PHASE = {
    "stealth": "stealth",
    "announcement": "announcement",
    "authority": "authority",
    "stealth phase": "stealth",
    "announcement phase": "announcement",
    "authority phase": "authority",
}


class DatabaseClient:
    """Postgres-backed data client with SheetsClient-compatible API."""

    def __init__(self):
        self._session_factory = get_sync_session_factory()
        logger.info("DatabaseClient initialized")

    def _session(self) -> Session:
        return self._session_factory()

    # ------------------------------------------------------------------
    # EngineControl (singleton row, id=1)
    # ------------------------------------------------------------------

    def get_engine_control(self) -> EngineControlDC:
        """Read the engine control settings."""
        with sync_session() as session:
            row = session.get(m.EngineControl, 1)
            if row is None:
                # Create default row if missing
                row = m.EngineControl(id=1)
                session.add(row)
                session.flush()

            return EngineControlDC(
                mode=EngineMode(row.mode),
                phase=Phase(row.phase),
                main_user_posting=row.main_user_posting,
                phantom_engagement=row.phantom_engagement,
                commenting=row.commenting,
                replying=row.replying,
                last_run=row.last_run,
            )

    def update_engine_control(self, updates: dict) -> None:
        """Update engine control fields.

        Args:
            updates: Dict of field names to new values.
                     Valid keys: mode, phase, main_user_posting,
                     phantom_engagement, commenting, replying, last_run.
        """
        with sync_session() as session:
            row = session.get(m.EngineControl, 1)
            if row is None:
                row = m.EngineControl(id=1)
                session.add(row)

            for key, value in updates.items():
                if hasattr(row, key):
                    # Convert enum values to strings for storage
                    if isinstance(value, (EngineMode, Phase)):
                        value = value.value
                    setattr(row, key, value)

    # ------------------------------------------------------------------
    # OutboundQueue
    # ------------------------------------------------------------------

    def get_ready_items(self, limit: int = 50) -> list[QueueItem]:
        """Get queue items with READY status, ordered by creation time."""
        with sync_session() as session:
            stmt = (
                select(m.OutboundQueue)
                .where(m.OutboundQueue.status == QueueStatus.READY.value)
                .order_by(m.OutboundQueue.created_at)
                .limit(limit)
            )
            rows = session.execute(stmt).scalars().all()

            return [
                QueueItem(
                    row_index=row.id,
                    post_id=row.post_id,
                    persona=row.persona,
                    content=row.draft_text,
                    content_type=row.action_type,
                    status=QueueStatus(row.status),
                    scheduled_time=(
                        row.scheduled_time.isoformat() if row.scheduled_time else None
                    ),
                    target_url=row.target_url,
                    notes=row.notes,
                    created_at=(
                        row.created_at.isoformat() if row.created_at else None
                    ),
                    executed_at=(
                        row.executed_at.isoformat() if row.executed_at else None
                    ),
                )
                for row in rows
            ]

    def update_queue_status(
        self,
        item: QueueItem,
        status: QueueStatus,
        notes: str = "",
    ) -> None:
        """Update the status of a queue item after execution."""
        with sync_session() as session:
            row = session.get(m.OutboundQueue, item.row_index)
            if row is None:
                logger.warning("Queue item %d not found", item.row_index)
                return

            row.status = status.value
            row.executed_at = datetime.now(timezone.utc)
            if notes:
                row.notes = f"{row.notes}\n{notes}".strip() if row.notes else notes

    def add_to_queue(
        self,
        post_id: str,
        persona: str,
        content: str,
        content_type: str,
        target_url: str = "",
        notes: str = "",
        scheduled_time: Optional[datetime] = None,
    ) -> int:
        """Add a new item to the outbound queue. Returns the new row ID."""
        with sync_session() as session:
            row = m.OutboundQueue(
                post_id=post_id,
                persona=persona,
                draft_text=content,
                action_type=content_type,
                target_url=target_url or None,
                notes=notes,
                scheduled_time=scheduled_time,
                status=QueueStatus.READY.value,
            )
            session.add(row)
            session.flush()
            return row.id

    # ------------------------------------------------------------------
    # CommentTargets
    # ------------------------------------------------------------------

    def get_comment_targets(self) -> list[CommentTargetDC]:
        """Get all comment targets, ordered by priority descending."""
        with sync_session() as session:
            stmt = select(m.CommentTarget).order_by(m.CommentTarget.priority.desc())
            rows = session.execute(stmt).scalars().all()

            return [
                CommentTargetDC(
                    name=row.name,
                    linkedin_url=row.linkedin_url,
                    category=row.category,
                    priority=row.priority,
                    last_comment_date=row.last_comment_date,
                    notes=row.notes,
                )
                for row in rows
            ]

    # ------------------------------------------------------------------
    # CommentTemplates
    # ------------------------------------------------------------------

    def get_comment_templates(
        self, persona: str = "MainUser"
    ) -> list[CommentTemplateDC]:
        """Get comment templates, optionally filtered by persona."""
        with sync_session() as session:
            stmt = select(m.CommentTemplate)
            if persona:
                stmt = stmt.where(m.CommentTemplate.persona == persona)
            rows = session.execute(stmt).scalars().all()

            return [
                CommentTemplateDC(
                    template_id=str(row.id),
                    template_text=row.template_text,
                    tone=row.tone,
                    category=row.category,
                    safety_flag=row.safety_flag,
                    example_use=row.example_use,
                    persona=row.persona,
                    use_count=row.use_count,
                )
                for row in rows
            ]

    # ------------------------------------------------------------------
    # ReplyRules
    # ------------------------------------------------------------------

    def get_reply_rules(self) -> list[ReplyRuleDC]:
        """Get all reply rules with non-empty triggers."""
        with sync_session() as session:
            stmt = select(m.ReplyRule).where(m.ReplyRule.trigger != "")
            rows = session.execute(stmt).scalars().all()

            return [
                ReplyRuleDC(
                    condition_type=row.condition_type,
                    trigger=row.trigger,
                    action=ReplyAction(row.action),
                    notes=row.notes,
                )
                for row in rows
            ]

    # ------------------------------------------------------------------
    # SafetyTerms
    # ------------------------------------------------------------------

    def get_safety_terms(self) -> list[SafetyTermDC]:
        """Get all safety terms."""
        with sync_session() as session:
            rows = session.execute(select(m.SafetyTerm)).scalars().all()

            return [
                SafetyTermDC(term=row.term, response=row.response)
                for row in rows
            ]

    # ------------------------------------------------------------------
    # ScheduleConfigs
    # ------------------------------------------------------------------

    def get_schedule_configs(self) -> list[ScheduleConfigDC]:
        """Get all schedule configurations."""
        with sync_session() as session:
            rows = session.execute(select(m.ScheduleConfig)).scalars().all()

            return [
                ScheduleConfigDC(
                    mode=row.phase,
                    posts_per_week=row.posts_per_week,
                    comments_per_day_min=row.comments_per_day_min,
                    comments_per_day_max=row.comments_per_day_max,
                    phantom_comments_min=row.phantom_comments_min,
                    phantom_comments_max=row.phantom_comments_max,
                    min_delay_sec=row.min_delay_sec,
                    max_likes_per_day=row.max_likes_per_day,
                )
                for row in rows
            ]

    def get_schedule_for_phase(self, phase: Phase) -> Optional[ScheduleConfigDC]:
        """Get the ScheduleConfig matching the current phase."""
        configs = self.get_schedule_configs()
        phase_value = phase.value.lower()
        for config in configs:
            mapped = _SCHEDULE_MODE_TO_PHASE.get(config.mode.lower(), "")
            if mapped == phase_value:
                return config
        return None

    # ------------------------------------------------------------------
    # ContentBank
    # ------------------------------------------------------------------

    def get_content_bank(self, ready_only: bool = False) -> list[ContentBankItem]:
        """Get content bank items."""
        with sync_session() as session:
            stmt = select(m.ContentBank)
            if ready_only:
                stmt = stmt.where(m.ContentBank.ready == True)  # noqa: E712
            rows = session.execute(stmt).scalars().all()

            return [
                ContentBankItem(
                    item_id=row.id,
                    category=row.category,
                    post_type=row.post_type,
                    draft=row.draft,
                    safety_flag=row.safety_flag,
                    ready=row.ready,
                    last_used=row.last_used,
                    notes=row.notes,
                )
                for row in rows
            ]

    # ------------------------------------------------------------------
    # RepostBank
    # ------------------------------------------------------------------

    def get_repost_bank(self) -> list[RepostBankItem]:
        """Get all repost bank items."""
        with sync_session() as session:
            rows = session.execute(select(m.RepostBank)).scalars().all()

            return [
                RepostBankItem(
                    item_id=row.id,
                    source_name=row.source_name,
                    source_url=row.source_url,
                    summary=row.summary,
                    commentary_prompt=row.commentary_prompt,
                    safety_flag=row.safety_flag,
                    last_used=row.last_used,
                    notes=row.notes,
                )
                for row in rows
            ]

    # ------------------------------------------------------------------
    # ActivityWindows
    # ------------------------------------------------------------------

    def get_activity_windows(self) -> list[ActivityWindowDC]:
        """Get all activity windows."""
        with sync_session() as session:
            rows = session.execute(select(m.ActivityWindow)).scalars().all()

            return [
                ActivityWindowDC(
                    window_name=row.window_name,
                    start_hour=row.start_hour,
                    end_hour=row.end_hour,
                    days_of_week=row.days_of_week,
                    enabled=row.enabled,
                )
                for row in rows
            ]

    # ------------------------------------------------------------------
    # SystemLog (append-only)
    # ------------------------------------------------------------------

    def log(
        self,
        action: str,
        persona: str = "",
        target: str = "",
        status: str = "OK",
        details: str = "",
        error: str = "",
        *,
        module: str = "",
        safety: str = "Safe",
        notes: str = "",
    ) -> None:
        """Append an entry to the system log.

        Accepts both SheetsClient.log() and DatabaseClient-native signatures:
          SheetsClient: log(action, persona, target, status, details, error)
          Native:       log(action, target=, module=, status=, notes=, error=)

        ``details`` is mapped to ``notes`` when ``notes`` is empty.
        ``persona`` is prepended to ``notes`` as ``[persona]`` when provided.
        """
        # Merge details → notes
        effective_notes = notes or details
        if persona and effective_notes:
            effective_notes = f"[{persona}] {effective_notes}"
        elif persona:
            effective_notes = f"[{persona}]"

        with sync_session() as session:
            entry = m.SystemLog(
                module=module,
                action=action,
                target=target,
                result=status if not error else f"FAILED: {error}",
                safety=safety,
                notes=effective_notes,
            )
            session.add(entry)
        logger.debug("Logged: %s %s → %s", action, target, status)

    def append_system_log(self, entry: SystemLogEntry) -> None:
        """Append a SystemLogEntry to the log."""
        self.log(
            action=entry.action,
            target=entry.target,
            module=entry.module,
            status=entry.result,
            safety=entry.safety,
            notes=entry.notes,
        )

    # ------------------------------------------------------------------
    # Generic tab CRUD (API layer compatibility)
    # ------------------------------------------------------------------

    def get_tab_data(
        self, tab: str, range_spec: str = "A:Z"
    ) -> tuple[list[str], list[list[str]], int]:
        """Read header + all data rows from a table.

        Returns: (header, data_rows, total_rows).
        Maps Sheet tab names to Postgres tables.
        """
        table_map = {
            "OutboundQueue": m.OutboundQueue,
            "CommentTargets": m.CommentTarget,
            "CommentTemplates": m.CommentTemplate,
            "ReplyRules": m.ReplyRule,
            "SafetyTerms": m.SafetyTerm,
            "ScheduleControl": m.ScheduleConfig,
            "EngineControl": m.EngineControl,
            "SystemLog": m.SystemLog,
            "ContentBank": m.ContentBank,
            "RepostBank": m.RepostBank,
            "ActivityWindows": m.ActivityWindow,
        }

        model_cls = table_map.get(tab)
        if model_cls is None:
            logger.warning("Unknown tab: %s", tab)
            return [], [], 0

        with sync_session() as session:
            rows = session.execute(select(model_cls)).scalars().all()
            if not rows:
                return [], [], 0

            # Build header from column names
            columns = [c.key for c in model_cls.__table__.columns]
            data = []
            for row in rows:
                data.append(
                    [str(getattr(row, col, "")) for col in columns]
                )
            return columns, data, len(data)

    def update_tab_row(
        self, tab: str, row_index: int, col_name: str, value: str
    ) -> None:
        """Update a single cell in a table row.

        row_index is the primary key ID (not a sheet row number).
        """
        table_map = {
            "OutboundQueue": m.OutboundQueue,
            "CommentTargets": m.CommentTarget,
            "CommentTemplates": m.CommentTemplate,
            "ReplyRules": m.ReplyRule,
            "SafetyTerms": m.SafetyTerm,
            "ScheduleControl": m.ScheduleConfig,
            "EngineControl": m.EngineControl,
            "ContentBank": m.ContentBank,
            "RepostBank": m.RepostBank,
            "ActivityWindows": m.ActivityWindow,
        }

        model_cls = table_map.get(tab)
        if model_cls is None:
            logger.warning("Unknown tab for update: %s", tab)
            return

        with sync_session() as session:
            row = session.get(model_cls, row_index)
            if row and hasattr(row, col_name):
                setattr(row, col_name, value)

    def append_tab_row(
        self, tab: str, header: list[str], row_dict: dict
    ) -> None:
        """Append a new row to a table.

        header is ignored (Sheets artifact). row_dict maps column names
        to values.
        """
        table_map = {
            "OutboundQueue": m.OutboundQueue,
            "CommentTargets": m.CommentTarget,
            "CommentTemplates": m.CommentTemplate,
            "ReplyRules": m.ReplyRule,
            "SafetyTerms": m.SafetyTerm,
            "ScheduleControl": m.ScheduleConfig,
            "ContentBank": m.ContentBank,
            "RepostBank": m.RepostBank,
            "ActivityWindows": m.ActivityWindow,
        }

        model_cls = table_map.get(tab)
        if model_cls is None:
            logger.warning("Unknown tab for append: %s", tab)
            return

        # Map Sheet column names to DB column names
        col_mapping = self._sheet_to_db_columns(tab)
        db_kwargs = {}
        for sheet_col, value in row_dict.items():
            db_col = col_mapping.get(sheet_col, sheet_col.lower())
            if hasattr(model_cls, db_col):
                # Type coercions
                col_obj = model_cls.__table__.columns.get(db_col)
                if col_obj is not None:
                    if str(col_obj.type) == "BOOLEAN":
                        value = str(value).upper() in ("TRUE", "1", "YES")
                    elif str(col_obj.type) == "INTEGER":
                        try:
                            value = int(float(value)) if value else 0
                        except (ValueError, TypeError):
                            value = 0
                db_kwargs[db_col] = value

        with sync_session() as session:
            row = model_cls(**db_kwargs)
            session.add(row)

    def delete_tab_row(self, tab: str, row_index: int) -> None:
        """Delete a row from a table by primary key."""
        table_map = {
            "OutboundQueue": m.OutboundQueue,
            "CommentTargets": m.CommentTarget,
            "CommentTemplates": m.CommentTemplate,
            "ReplyRules": m.ReplyRule,
            "SafetyTerms": m.SafetyTerm,
            "ScheduleControl": m.ScheduleConfig,
            "ContentBank": m.ContentBank,
            "RepostBank": m.RepostBank,
            "ActivityWindows": m.ActivityWindow,
        }

        model_cls = table_map.get(tab)
        if model_cls is None:
            return

        with sync_session() as session:
            row = session.get(model_cls, row_index)
            if row:
                session.delete(row)

    @staticmethod
    def _sheet_to_db_columns(tab: str) -> dict[str, str]:
        """Map Google Sheet column names to database column names."""
        common = {
            "ID": "id",
            "Notes": "notes",
        }
        tab_maps = {
            "OutboundQueue": {
                "Timestamp": "created_at",
                "ActionType": "action_type",
                "Persona": "persona",
                "TargetName": "target_name",
                "TargetURL": "target_url",
                "DraftText": "draft_text",
                "Status": "status",
                "ScheduledTime": "scheduled_time",
            },
            "CommentTargets": {
                "Name": "name",
                "LinkedInURL": "linkedin_url",
                "Category": "category",
                "Priority": "priority",
                "LastCommentDate": "last_comment_date",
            },
            "CommentTemplates": {
                "TemplateText": "template_text",
                "Tone": "tone",
                "Category": "category",
                "SafetyFlag": "safety_flag",
                "ExampleUse": "example_use",
                "Persona": "persona",
            },
            "ReplyRules": {
                "ConditionType": "condition_type",
                "Trigger": "trigger",
                "Action": "action",
            },
            "SafetyTerms": {
                "Term": "term",
                "Response": "response",
            },
            "ScheduleControl": {
                "Mode": "phase",
                "PostsPerWeek": "posts_per_week",
                "CommentsPerDay": "comments_per_day_min",
                "CommentsPerDayMax": "comments_per_day_max",
                "PhantomComments": "phantom_comments_min",
                "PhantomCommentsMax": "phantom_comments_max",
                "MinDelaySec": "min_delay_sec",
                "MaxLikesPerDay": "max_likes_per_day",
            },
            "ContentBank": {
                "Category": "category",
                "PostType": "post_type",
                "Draft": "draft",
                "SafetyFlag": "safety_flag",
                "Ready": "ready",
                "LastUsed": "last_used",
            },
            "RepostBank": {
                "SourceName": "source_name",
                "SourceURL": "source_url",
                "Summary": "summary",
                "CommentaryPrompt": "commentary_prompt",
                "SafetyFlag": "safety_flag",
                "LastUsed": "last_used",
            },
            "ActivityWindows": {
                "WindowName": "window_name",
                "StartHour": "start_hour",
                "EndHour": "end_hour",
                "DaysOfWeek": "days_of_week",
                "Enabled": "enabled",
            },
        }
        result = dict(common)
        result.update(tab_maps.get(tab, {}))
        return result

    # ------------------------------------------------------------------
    # SystemLog (read — with pagination and filtering)
    # ------------------------------------------------------------------

    def get_system_log(
        self,
        limit: int = 50,
        offset: int = 0,
        action_filter: str = "",
        module_filter: str = "",
        date_from: str = "",
        date_to: str = "",
    ) -> tuple[list[dict], int]:
        """Get system log entries with pagination and filtering.

        Returns: (entries, total_count).
        """
        with sync_session() as session:
            stmt = select(m.SystemLog)
            count_stmt = select(func.count(m.SystemLog.id))

            if action_filter:
                stmt = stmt.where(m.SystemLog.action.ilike(f"%{action_filter}%"))
                count_stmt = count_stmt.where(m.SystemLog.action.ilike(f"%{action_filter}%"))
            if module_filter:
                stmt = stmt.where(m.SystemLog.module.ilike(f"%{module_filter}%"))
                count_stmt = count_stmt.where(m.SystemLog.module.ilike(f"%{module_filter}%"))
            if date_from:
                stmt = stmt.where(m.SystemLog.timestamp >= date_from)
                count_stmt = count_stmt.where(m.SystemLog.timestamp >= date_from)
            if date_to:
                stmt = stmt.where(m.SystemLog.timestamp <= date_to)
                count_stmt = count_stmt.where(m.SystemLog.timestamp <= date_to)

            total = session.execute(count_stmt).scalar() or 0

            stmt = (
                stmt
                .order_by(m.SystemLog.timestamp.desc())
                .offset(offset)
                .limit(limit)
            )
            rows = session.execute(stmt).scalars().all()

            entries = [
                {
                    "id": row.id,
                    "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                    "module": row.module or "",
                    "action": row.action or "",
                    "target": row.target or "",
                    "result": row.result or "",
                    "safety": row.safety or "",
                    "notes": row.notes or "",
                }
                for row in rows
            ]
            return entries, total

    def get_error_log(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Get system log entries where result indicates failure.

        Returns: (error_entries, total_error_count).
        """
        with sync_session() as session:
            error_filter = m.SystemLog.result.ilike("%FAIL%")
            count_stmt = select(func.count(m.SystemLog.id)).where(error_filter)
            total = session.execute(count_stmt).scalar() or 0

            stmt = (
                select(m.SystemLog)
                .where(error_filter)
                .order_by(m.SystemLog.timestamp.desc())
                .offset(offset)
                .limit(limit)
            )
            rows = session.execute(stmt).scalars().all()

            entries = [
                {
                    "id": row.id,
                    "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                    "module": row.module or "",
                    "action": row.action or "",
                    "target": row.target or "",
                    "result": row.result or "",
                    "safety": row.safety or "",
                    "notes": row.notes or "",
                }
                for row in rows
            ]
            return entries, total

    # ------------------------------------------------------------------
    # OutboundQueue (extended — dashboard management)
    # ------------------------------------------------------------------

    def get_queue_items(
        self,
        status_filter: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Get queue items with optional status filter and pagination.

        Returns: (items, total_count).
        """
        with sync_session() as session:
            stmt = select(m.OutboundQueue)
            count_stmt = select(func.count(m.OutboundQueue.id))

            if status_filter:
                stmt = stmt.where(m.OutboundQueue.status == status_filter.upper())
                count_stmt = count_stmt.where(
                    m.OutboundQueue.status == status_filter.upper()
                )

            total = session.execute(count_stmt).scalar() or 0

            stmt = (
                stmt
                .order_by(m.OutboundQueue.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            rows = session.execute(stmt).scalars().all()

            items = [
                {
                    "id": row.id,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "post_id": row.post_id or "",
                    "action_type": row.action_type or "",
                    "persona": row.persona or "",
                    "target_name": row.target_name or "",
                    "target_url": row.target_url or "",
                    "draft_text": row.draft_text or "",
                    "status": row.status or "",
                    "scheduled_time": (
                        row.scheduled_time.isoformat() if row.scheduled_time else None
                    ),
                    "executed_at": (
                        row.executed_at.isoformat() if row.executed_at else None
                    ),
                    "notes": row.notes or "",
                }
                for row in rows
            ]
            return items, total

    def update_queue_item(
        self,
        item_id: int,
        updates: dict,
    ) -> Optional[dict]:
        """Update a queue item by ID. Returns updated item or None."""
        with sync_session() as session:
            row = session.get(m.OutboundQueue, item_id)
            if row is None:
                return None

            for key, value in updates.items():
                if hasattr(row, key) and key != "id":
                    setattr(row, key, value)

            session.flush()
            return {
                "id": row.id,
                "status": row.status,
                "draft_text": row.draft_text or "",
                "notes": row.notes or "",
            }

    def get_queue_stats(self) -> dict:
        """Get counts of queue items grouped by status."""
        with sync_session() as session:
            stmt = (
                select(m.OutboundQueue.status, func.count(m.OutboundQueue.id))
                .group_by(m.OutboundQueue.status)
            )
            results = session.execute(stmt).all()
            stats = {status: count for status, count in results}
            stats["total"] = sum(stats.values())
            return stats

    # ------------------------------------------------------------------
    # ScheduleConfig (update — missing from original)
    # ------------------------------------------------------------------

    def update_schedule_config(self, mode: str, updates: dict) -> bool:
        """Update schedule config for a given mode/phase. Returns True if found."""
        with sync_session() as session:
            stmt = select(m.ScheduleConfig).where(m.ScheduleConfig.phase == mode)
            row = session.execute(stmt).scalar_one_or_none()
            if row is None:
                return False

            for key, value in updates.items():
                if hasattr(row, key) and key not in ("id", "phase"):
                    setattr(row, key, value)
            return True

    # ------------------------------------------------------------------
    # Pipeline runs (new — not in SheetsClient)
    # ------------------------------------------------------------------

    def create_pipeline_run(
        self,
        trigger_type: str = "scheduled",
        phase: str = "",
    ) -> int:
        """Create a new pipeline run record. Returns the run ID."""
        with sync_session() as session:
            run = m.PipelineRun(
                trigger_type=trigger_type,
                phase=phase,
                status=m.PipelineStatusEnum.RUNNING.value,
            )
            session.add(run)
            session.flush()
            return run.id

    def complete_pipeline_run(
        self,
        run_id: int,
        *,
        status: str = "completed",
        posts_made: int = 0,
        comments_made: int = 0,
        replies_made: int = 0,
        phantom_actions: int = 0,
        errors: Optional[dict] = None,
        summary: str = "",
    ) -> None:
        """Mark a pipeline run as completed."""
        with sync_session() as session:
            run = session.get(m.PipelineRun, run_id)
            if run:
                run.completed_at = datetime.now(timezone.utc)
                run.status = status
                run.posts_made = posts_made
                run.comments_made = comments_made
                run.replies_made = replies_made
                run.phantom_actions = phantom_actions
                run.errors = errors
                run.summary = summary

    def get_pipeline_runs(self, limit: int = 50) -> list[dict]:
        """Get recent pipeline runs."""
        with sync_session() as session:
            stmt = (
                select(m.PipelineRun)
                .order_by(m.PipelineRun.started_at.desc())
                .limit(limit)
            )
            rows = session.execute(stmt).scalars().all()

            return [
                {
                    "id": row.id,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                    "trigger_type": row.trigger_type,
                    "status": row.status,
                    "phase": row.phase,
                    "posts_made": row.posts_made,
                    "comments_made": row.comments_made,
                    "replies_made": row.replies_made,
                    "phantom_actions": row.phantom_actions,
                    "errors": row.errors,
                    "summary": row.summary,
                }
                for row in rows
            ]

    # ------------------------------------------------------------------
    # Feed sources (new — replaces config/feeds.json)
    # ------------------------------------------------------------------

    def get_feed_sources(self, active_only: bool = True) -> list[dict]:
        """Get RSS feed sources."""
        with sync_session() as session:
            stmt = select(m.FeedSource)
            if active_only:
                stmt = stmt.where(m.FeedSource.active == True)  # noqa: E712
            rows = session.execute(stmt).scalars().all()

            return [
                {
                    "id": row.id,
                    "name": row.name,
                    "url": row.url,
                    "type": row.feed_type,
                    "category": row.category,
                    "active": row.active,
                    "last_fetched": (
                        row.last_fetched.isoformat() if row.last_fetched else None
                    ),
                    "created_at": (
                        row.created_at.isoformat() if row.created_at else None
                    ),
                }
                for row in rows
            ]

    def create_feed_source(
        self,
        name: str,
        url: str,
        feed_type: str = "rss",
        category: str = "",
        active: bool = True,
    ) -> int:
        """Create a new feed source. Returns the new ID."""
        with sync_session() as session:
            row = m.FeedSource(
                name=name,
                url=url,
                feed_type=feed_type,
                category=category,
                active=active,
            )
            session.add(row)
            session.flush()
            return row.id

    def update_feed_source(self, feed_id: int, updates: dict) -> bool:
        """Update a feed source by ID. Returns True if found."""
        with sync_session() as session:
            row = session.get(m.FeedSource, feed_id)
            if row is None:
                return False

            for key, value in updates.items():
                db_key = key if key != "type" else "feed_type"
                if hasattr(row, db_key) and db_key not in ("id", "created_at"):
                    setattr(row, db_key, value)
            return True

    def delete_feed_source(self, feed_id: int) -> bool:
        """Delete a feed source by ID. Returns True if found."""
        with sync_session() as session:
            row = session.get(m.FeedSource, feed_id)
            if row is None:
                return False
            session.delete(row)
            return True

    # ------------------------------------------------------------------
    # Webhook events (LinkedIn social action notifications)
    # ------------------------------------------------------------------

    def create_webhook_event(self, event_data: dict) -> int:
        """Insert a webhook event. Returns the new ID."""
        with sync_session() as session:
            row = m.WebhookEvent(
                event_type=event_data.get("event_type", "ORGANIZATION_SOCIAL_ACTION_NOTIFICATIONS"),
                action=event_data.get("action", ""),
                notification_id=event_data["notification_id"],
                organization_urn=event_data.get("organization_urn", ""),
                source_post_urn=event_data.get("source_post_urn"),
                generated_activity_urn=event_data.get("generated_activity_urn", ""),
                actor_urn=event_data.get("actor_urn"),
                comment_text=event_data.get("comment_text"),
                raw_payload=event_data.get("raw_payload"),
                processed=event_data.get("processed", False),
                queue_item_id=event_data.get("queue_item_id"),
            )
            session.add(row)
            session.flush()
            return row.id

    def get_webhook_event_by_notification_id(self, notification_id: int) -> Optional[dict]:
        """Look up a webhook event by LinkedIn notification_id (for deduplication)."""
        with sync_session() as session:
            stmt = select(m.WebhookEvent).where(
                m.WebhookEvent.notification_id == notification_id
            )
            row = session.execute(stmt).scalar_one_or_none()
            if row is None:
                return None
            return {
                "id": row.id,
                "received_at": row.received_at.isoformat() if row.received_at else None,
                "event_type": row.event_type,
                "action": row.action,
                "notification_id": row.notification_id,
                "organization_urn": row.organization_urn,
                "source_post_urn": row.source_post_urn,
                "generated_activity_urn": row.generated_activity_urn,
                "actor_urn": row.actor_urn,
                "comment_text": row.comment_text,
                "processed": row.processed,
                "queue_item_id": row.queue_item_id,
            }

    def get_webhook_events(
        self,
        limit: int = 50,
        offset: int = 0,
        action_filter: str = "",
        processed: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        """List webhook events with filtering. Returns (events, total_count)."""
        with sync_session() as session:
            stmt = select(m.WebhookEvent)
            count_stmt = select(func.count(m.WebhookEvent.id))

            if action_filter:
                stmt = stmt.where(m.WebhookEvent.action == action_filter)
                count_stmt = count_stmt.where(m.WebhookEvent.action == action_filter)
            if processed is not None:
                stmt = stmt.where(m.WebhookEvent.processed == processed)
                count_stmt = count_stmt.where(m.WebhookEvent.processed == processed)

            total = session.execute(count_stmt).scalar_one()

            stmt = (
                stmt
                .order_by(m.WebhookEvent.received_at.desc())
                .offset(offset)
                .limit(limit)
            )
            rows = session.execute(stmt).scalars().all()

            events = [
                {
                    "id": row.id,
                    "received_at": row.received_at.isoformat() if row.received_at else None,
                    "event_type": row.event_type,
                    "action": row.action,
                    "notification_id": row.notification_id,
                    "organization_urn": row.organization_urn,
                    "source_post_urn": row.source_post_urn,
                    "generated_activity_urn": row.generated_activity_urn,
                    "actor_urn": row.actor_urn,
                    "comment_text": row.comment_text,
                    "processed": row.processed,
                    "queue_item_id": row.queue_item_id,
                }
                for row in rows
            ]
            return events, total

    def update_webhook_event_queue_link(self, event_id: int, queue_item_id: int) -> None:
        """Link a webhook event to its auto-created queue item."""
        with sync_session() as session:
            row = session.get(m.WebhookEvent, event_id)
            if row:
                row.queue_item_id = queue_item_id
                row.processed = True
