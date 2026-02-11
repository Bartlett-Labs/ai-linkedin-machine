"""
Google Sheets API client - the execution bridge.

Reads queued items from the OutboundQueue, updates their status after
execution, reads configuration tabs (CommentTargets, CommentTemplates,
ReplyRules, SafetyTerms, ScheduleControl, EngineControl), and writes
to SystemLog after every action.

Supports both service account and OAuth authentication.
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as OAuthCredentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from sheets.models import (
    QueueItem,
    QueueStatus,
    CommentTarget,
    CommentTemplate,
    ReplyRule,
    ReplyAction,
    SafetyTerm,
    ScheduleConfig,
    EngineControl,
    EngineMode,
    Phase,
    SystemLogEntry,
    ContentBankItem,
    RepostBankItem,
)

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Tab names in the Sheet — must match exactly
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

# Map ScheduleControl "Mode" values to Phase enum values
_SCHEDULE_MODE_TO_PHASE = {
    "stealth": "stealth",
    "postannouncement": "announcement",
    "announcement": "announcement",
    "authority": "authority",
}


def _parse_range(value, default_min: int, default_max: int) -> tuple[int, int]:
    """Parse a range like '7-12', a single number, or return defaults.

    Handles: "7-12" -> (7, 12), "10" -> (10, 10), None -> defaults.
    """
    if value is None:
        return default_min, default_max
    s = str(value).strip()
    if not s:
        return default_min, default_max
    # Range format: "7-12"
    if "-" in s and not s.startswith("-"):
        parts = s.split("-", 1)
        try:
            return int(float(parts[0])), int(float(parts[1]))
        except (ValueError, IndexError):
            return default_min, default_max
    # Single number
    try:
        n = int(float(s))
        return n, n
    except ValueError:
        return default_min, default_max


def _derive_module(action: str) -> str:
    """Derive the Module name from an action string for SystemLog."""
    a = action.upper()
    if "COMMENT" in a:
        return "Commenter"
    if "POST" in a or "QUEUE" in a:
        return "Poster"
    if "REPLY" in a:
        return "Replier"
    if "PHANTOM" in a:
        return "PhantomEngine"
    if "ORCHESTRATOR" in a:
        return "Orchestrator"
    if "CHALLENGE" in a:
        return "SafetyMonitor"
    if "HEARTBEAT" in a or "ALIVE" in a:
        return "Heartbeat"
    if "INGEST" in a:
        return "Ingestion"
    if "SAFETY" in a or "BLOCK" in a:
        return "SafetyFilter"
    return "Engine"


class SheetsClient:
    """Connects to the LinkedIn Stealth Engine Google Sheet."""

    def __init__(
        self,
        spreadsheet_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
    ):
        self.spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEET_ID")
        self._credentials_path = credentials_path or os.getenv(
            "GOOGLE_CREDENTIALS_PATH", "credentials/service_account.json"
        )
        self._token_path = token_path or os.getenv(
            "GOOGLE_TOKEN_PATH", "credentials/token.json"
        )
        self._service = None

    def _authenticate(self):
        """Authenticate via service account or OAuth token."""
        creds = None

        # Try service account first
        if os.path.exists(self._credentials_path):
            creds = ServiceAccountCredentials.from_service_account_file(
                self._credentials_path, scopes=SCOPES
            )
            logger.info("Authenticated via service account")
        # Fall back to OAuth token
        elif os.path.exists(self._token_path):
            creds = OAuthCredentials.from_authorized_user_file(
                self._token_path, SCOPES
            )
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            logger.info("Authenticated via OAuth token")
        else:
            raise FileNotFoundError(
                f"No credentials found. Place a service account JSON at "
                f"{self._credentials_path} or OAuth token at {self._token_path}"
            )

        self._service = build("sheets", "v4", credentials=creds)

    @property
    def sheets(self):
        if self._service is None:
            self._authenticate()
        return self._service.spreadsheets()

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    def _read_range(self, range_name: str) -> list[list[str]]:
        """Read a range from the spreadsheet. Returns list of rows."""
        result = (
            self.sheets.values()
            .get(spreadsheetId=self.spreadsheet_id, range=range_name)
            .execute()
        )
        return result.get("values", [])

    def _update_cells(self, range_name: str, values: list[list]) -> None:
        """Write values to a specific range."""
        self.sheets.values().update(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body={"values": values},
        ).execute()

    def _append_row(self, tab: str, values: list) -> None:
        """Append a row to the bottom of a tab."""
        self.sheets.values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"{tab}!A:Z",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [values]},
        ).execute()

    # ------------------------------------------------------------------
    # OutboundQueue
    # Sheet columns: Timestamp, ActionType, TargetName, TargetURL,
    #                DraftText, Status, Notes, ExecuteLink, CopyReady
    # ------------------------------------------------------------------

    def get_ready_items(self, limit: int = 50) -> list[QueueItem]:
        """Read items from OutboundQueue with status=READY, oldest first."""
        rows = self._read_range(f"{TAB_OUTBOUND_QUEUE}!A:K")
        if not rows:
            return []

        header = rows[0]
        items = []
        for idx, row in enumerate(rows[1:], start=2):  # Row 2 in Sheet
            row_dict = dict(zip(header, row + [""] * (len(header) - len(row))))
            if row_dict.get("Status", "").upper() == "READY":
                # Support both column naming conventions
                content = (
                    row_dict.get("Content")
                    or row_dict.get("DraftText")
                    or ""
                )
                content_type = (
                    row_dict.get("ContentType")
                    or row_dict.get("ActionType")
                    or "post"
                )
                post_id = (
                    row_dict.get("PostID")
                    or row_dict.get("Timestamp", "")
                )
                persona = row_dict.get("Persona", "MainUser")
                target_url = (
                    row_dict.get("TargetURL")
                    or ""
                )

                items.append(
                    QueueItem(
                        row_index=idx,
                        post_id=post_id,
                        persona=persona,
                        content=content,
                        content_type=content_type,
                        status=QueueStatus.READY,
                        scheduled_time=row_dict.get("ScheduledTime"),
                        target_url=target_url,
                        notes=row_dict.get("Notes"),
                        created_at=row_dict.get("CreatedAt") or row_dict.get("Timestamp"),
                    )
                )
                if len(items) >= limit:
                    break

        logger.info("Found %d READY items in OutboundQueue", len(items))
        return items

    def update_queue_status(
        self,
        item: QueueItem,
        status: QueueStatus,
        notes: str = "",
    ) -> None:
        """Update the status of a queue item after execution.

        Writes status to the Status column. Combines the execution
        timestamp and any notes into the Notes column (since the sheet
        has no dedicated ExecutedAt column).
        """
        rows = self._read_range(f"{TAB_OUTBOUND_QUEUE}!A1:K1")
        if not rows:
            return
        header = rows[0]

        status_col = _col_letter(header.index("Status")) if "Status" in header else "F"
        notes_col = _col_letter(header.index("Notes")) if "Notes" in header else "G"

        row = item.row_index
        # Write status
        self._update_cells(
            f"{TAB_OUTBOUND_QUEUE}!{status_col}{row}",
            [[status.value]],
        )
        # Write execution timestamp + notes into Notes column
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        note_text = f"[{timestamp}] {status.value}"
        if notes:
            note_text += f" - {notes}"
        self._update_cells(
            f"{TAB_OUTBOUND_QUEUE}!{notes_col}{row}",
            [[note_text]],
        )
        logger.info("Updated queue item row %d -> %s", row, status.value)

    # ------------------------------------------------------------------
    # CommentTargets
    # Sheet columns: ID, Name, LinkedInURL, Category, Priority,
    #                LastCommentDate, Notes
    # ------------------------------------------------------------------

    def get_comment_targets(self) -> list[CommentTarget]:
        """Read all comment targets from the Sheet."""
        rows = self._read_range(f"{TAB_COMMENT_TARGETS}!A:G")
        if len(rows) < 2:
            return []

        header = rows[0]
        targets = []
        for row in rows[1:]:
            d = dict(zip(header, row + [""] * (len(header) - len(row))))
            url = d.get("LinkedInURL", "").strip()
            if not url:
                continue
            targets.append(
                CommentTarget(
                    name=d.get("Name", ""),
                    linkedin_url=url,
                    category=d.get("Category", "network"),
                    priority=int(d.get("Priority", 1) or 1),
                    last_comment_date=d.get("LastCommentDate"),
                    notes=d.get("Notes"),
                )
            )
        return targets

    # ------------------------------------------------------------------
    # CommentTemplates
    # Sheet columns: ID, TemplateText, Tone, Category, SafetyFlag,
    #                ExampleUse
    # ------------------------------------------------------------------

    def get_comment_templates(self, persona: str = "MainUser") -> list[CommentTemplate]:
        """Read comment templates, optionally filtered by persona.

        Note: The sheet currently has no Persona column, so all templates
        default to MainUser. If a Persona column is added later, it will
        be picked up automatically.
        """
        rows = self._read_range(f"{TAB_COMMENT_TEMPLATES}!A:F")
        if len(rows) < 2:
            return []

        header = rows[0]
        templates = []
        for row in rows[1:]:
            d = dict(zip(header, row + [""] * (len(header) - len(row))))
            t = CommentTemplate(
                template_id=str(d.get("ID", "")),
                template_text=d.get("TemplateText", ""),
                tone=d.get("Tone", ""),
                category=d.get("Category", ""),
                safety_flag=int(float(d.get("SafetyFlag", 0) or 0)),
                example_use=d.get("ExampleUse", ""),
                persona=d.get("Persona", "MainUser"),
                use_count=int(d.get("UseCount", 0) or 0),
            )
            if t.template_text and (persona == "all" or t.persona == persona):
                templates.append(t)
        return templates

    # ------------------------------------------------------------------
    # ReplyRules
    # Sheet columns: ConditionType, Trigger, Action, Notes
    # ------------------------------------------------------------------

    def get_reply_rules(self) -> list[ReplyRule]:
        """Read reply rules (BLOCK/REPLY triggers).

        Rules with empty triggers are skipped to prevent accidental
        universal matches.
        """
        rows = self._read_range(f"{TAB_REPLY_RULES}!A:D")
        if len(rows) < 2:
            return []

        header = rows[0]
        rules = []
        for row in rows[1:]:
            d = dict(zip(header, row + [""] * (len(header) - len(row))))
            trigger = d.get("Trigger", "").strip()
            if not trigger:
                continue  # Skip rules with empty triggers
            rules.append(
                ReplyRule(
                    condition_type=d.get("ConditionType", ""),
                    trigger=trigger,
                    action=ReplyAction(d.get("Action", "IGNORE")),
                    notes=d.get("Notes"),
                )
            )
        return rules

    # ------------------------------------------------------------------
    # SafetyTerms
    # Sheet columns: Term, Response
    # ------------------------------------------------------------------

    def get_safety_terms(self) -> list[SafetyTerm]:
        """Read all safety terms from the Sheet."""
        rows = self._read_range(f"{TAB_SAFETY_TERMS}!A:B")
        if len(rows) < 2:
            return []

        header = rows[0]
        terms = []
        for row in rows[1:]:
            d = dict(zip(header, row + [""] * (len(header) - len(row))))
            term = d.get("Term", "").strip()
            if not term:
                continue
            terms.append(
                SafetyTerm(
                    term=term,
                    response=d.get("Response", "BLOCK"),
                )
            )
        return terms

    # ------------------------------------------------------------------
    # ScheduleControl
    # Sheet columns: Mode, PostsPerWeek, CommentsPerDay, PhantomComments,
    #                MinDelaySec, MaxLikesPerDay
    # ------------------------------------------------------------------

    def get_schedule_configs(self) -> list[ScheduleConfig]:
        """Read per-phase rate limits from ScheduleControl.

        CommentsPerDay and PhantomComments may be ranges (e.g. '7-12')
        or single numbers. MinDelaySec and MaxLikesPerDay are optional
        columns — if absent, defaults from the model are used.
        """
        rows = self._read_range(f"{TAB_SCHEDULE_CONTROL}!A:F")
        if len(rows) < 2:
            return []

        header = rows[0]
        configs = []
        for row in rows[1:]:
            d = dict(zip(header, row + [""] * (len(header) - len(row))))
            mode = d.get("Mode", "").strip()
            if not mode:
                continue

            posts_raw = d.get("PostsPerWeek", "2")
            try:
                posts_per_week = int(float(posts_raw))
            except (ValueError, TypeError):
                posts_per_week = 2

            cpd_min, cpd_max = _parse_range(
                d.get("CommentsPerDay"), 7, 12
            )
            pc_min, pc_max = _parse_range(
                d.get("PhantomComments"), 1, 2
            )

            delay_raw = d.get("MinDelaySec", "")
            try:
                min_delay_sec = int(float(delay_raw)) if delay_raw else 300
            except (ValueError, TypeError):
                min_delay_sec = 300

            likes_raw = d.get("MaxLikesPerDay", "")
            try:
                max_likes_per_day = int(float(likes_raw)) if likes_raw else 20
            except (ValueError, TypeError):
                max_likes_per_day = 20

            configs.append(
                ScheduleConfig(
                    mode=mode,
                    posts_per_week=posts_per_week,
                    comments_per_day_min=cpd_min,
                    comments_per_day_max=cpd_max,
                    phantom_comments_min=pc_min,
                    phantom_comments_max=pc_max,
                    min_delay_sec=min_delay_sec,
                    max_likes_per_day=max_likes_per_day,
                )
            )
        return configs

    def get_schedule_for_phase(self, phase: Phase) -> Optional[ScheduleConfig]:
        """Get the ScheduleConfig matching the current phase, if any."""
        configs = self.get_schedule_configs()
        phase_value = phase.value.lower()
        for config in configs:
            mapped = _SCHEDULE_MODE_TO_PHASE.get(config.mode.lower(), "")
            if mapped == phase_value:
                return config
        return None

    # ------------------------------------------------------------------
    # EngineControl
    # Key-value pairs in columns A and B (no header row)
    # ------------------------------------------------------------------

    def get_engine_control(self) -> EngineControl:
        """Read current engine settings (mode, phase, toggles)."""
        rows = self._read_range(f"{TAB_ENGINE_CONTROL}!A:B")
        if len(rows) < 2:
            return EngineControl()

        settings = {}
        for row in rows:
            if len(row) >= 2:
                key = row[0].strip() if isinstance(row[0], str) else str(row[0])
                val = row[1].strip() if isinstance(row[1], str) else str(row[1])
                settings[key] = val

        return EngineControl(
            mode=EngineMode(settings.get("Mode", "DryRun")),
            phase=Phase(settings.get("Phase", "stealth")),
            main_user_posting=settings.get("MainUserPosting", "TRUE").upper() == "TRUE",
            phantom_engagement=settings.get("PhantomEngagement", "TRUE").upper() == "TRUE",
            commenting=settings.get("Commenting", "TRUE").upper() == "TRUE",
            replying=settings.get("Replying", "TRUE").upper() == "TRUE",
            last_run=settings.get("LastRun"),
        )

    def update_last_run(self) -> None:
        """Update the LastRun timestamp in EngineControl."""
        rows = self._read_range(f"{TAB_ENGINE_CONTROL}!A:B")
        for idx, row in enumerate(rows):
            if row and row[0].strip() == "LastRun":
                self._update_cells(
                    f"{TAB_ENGINE_CONTROL}!B{idx + 1}",
                    [[datetime.utcnow().isoformat()]],
                )
                return

    # ------------------------------------------------------------------
    # SystemLog
    # Sheet columns: Timestamp, Module, Action, Target, Result,
    #                Safety, Notes
    # ------------------------------------------------------------------

    def log_action(self, entry: SystemLogEntry) -> None:
        """Append a log entry to SystemLog."""
        self._append_row(
            TAB_SYSTEM_LOG,
            [
                entry.timestamp,
                entry.module,
                entry.action,
                entry.target,
                entry.result,
                entry.safety,
                entry.notes,
            ],
        )

    def log(
        self,
        action: str,
        persona: str = "",
        target: str = "",
        status: str = "OK",
        details: str = "",
        error: str = "",
    ) -> None:
        """Convenience wrapper to log an action.

        Maps the call parameters to the sheet's column format:
        Timestamp, Module, Action, Target, Result, Safety, Notes.

        - Module is derived from the action name (e.g. COMMENT -> Commenter)
        - Safety is derived from the status/action context
        - Persona, details, and error are combined into Notes
        """
        module = _derive_module(action)

        # Derive safety status from action/status context
        status_upper = status.upper()
        if any(kw in status_upper for kw in ("BLOCK", "SAFETY", "FAIL")):
            safety = "Blocked"
        elif any(kw in action.upper() for kw in ("BLOCK", "SAFETY")):
            safety = "Blocked"
        else:
            safety = "Safe"

        # Build notes from persona, details, and error
        notes_parts = []
        if persona:
            notes_parts.append(f"[{persona}]")
        if details:
            notes_parts.append(details)
        if error:
            notes_parts.append(f"Error: {error}")
        notes = " | ".join(notes_parts) if notes_parts else ""

        self.log_action(
            SystemLogEntry(
                module=module,
                action=action,
                target=target,
                result=status,
                safety=safety,
                notes=notes,
            )
        )

    # ------------------------------------------------------------------
    # ContentBank
    # Sheet columns: ID, Category, PostType, Draft, SafetyFlag, Ready,
    #                LastUsed, Notes
    # ------------------------------------------------------------------

    def get_content_bank(self, ready_only: bool = True) -> list[ContentBankItem]:
        """Read content bank items."""
        rows = self._read_range(f"{TAB_CONTENT_BANK}!A:H")
        if len(rows) < 2:
            return []

        header = rows[0]
        items = []
        for row in rows[1:]:
            d = dict(zip(header, row + [""] * (len(header) - len(row))))
            ready = str(d.get("Ready", "TRUE")).upper() == "TRUE"
            if ready_only and not ready:
                continue
            items.append(
                ContentBankItem(
                    item_id=int(float(d.get("ID", 0) or 0)),
                    category=d.get("Category", ""),
                    post_type=d.get("PostType", ""),
                    draft=d.get("Draft", ""),
                    safety_flag=int(float(d.get("SafetyFlag", 0) or 0)),
                    ready=ready,
                    last_used=d.get("LastUsed") or None,
                    notes=d.get("Notes") or None,
                )
            )
        return items

    # ------------------------------------------------------------------
    # RepostBank
    # Sheet columns: ID, SourceName, SourceURL, Summary,
    #                CommentaryPrompt, SafetyFlag, LastUsed, Notes
    # ------------------------------------------------------------------

    def get_repost_bank(self) -> list[RepostBankItem]:
        """Read repost bank items."""
        rows = self._read_range(f"{TAB_REPOST_BANK}!A:H")
        if len(rows) < 2:
            return []

        header = rows[0]
        items = []
        for row in rows[1:]:
            d = dict(zip(header, row + [""] * (len(header) - len(row))))
            items.append(
                RepostBankItem(
                    item_id=int(float(d.get("ID", 0) or 0)),
                    source_name=d.get("SourceName", ""),
                    source_url=d.get("SourceURL", ""),
                    summary=d.get("Summary", ""),
                    commentary_prompt=d.get("CommentaryPrompt", ""),
                    safety_flag=int(float(d.get("SafetyFlag", 0) or 0)),
                    last_used=d.get("LastUsed") or None,
                    notes=d.get("Notes") or None,
                )
            )
        return items


def _col_letter(index: int) -> str:
    """Convert a 0-based column index to a letter (A, B, ..., Z, AA, ...)."""
    result = ""
    while index >= 0:
        result = chr(65 + index % 26) + result
        index = index // 26 - 1
    return result
