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
    ScheduleWindow,
    EngineControl,
    EngineMode,
    Phase,
    SystemLogEntry,
)

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Tab names in the Sheet
TAB_OUTBOUND_QUEUE = "OutboundQueue"
TAB_COMMENT_TARGETS = "CommentTargets"
TAB_COMMENT_TEMPLATES = "CommentTemplates"
TAB_REPLY_RULES = "ReplyRules"
TAB_SAFETY_TERMS = "SafetyTerms"
TAB_SCHEDULE_CONTROL = "ScheduleControl"
TAB_ENGINE_CONTROL = "EngineControl"
TAB_SYSTEM_LOG = "SystemLog"


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
                items.append(
                    QueueItem(
                        row_index=idx,
                        post_id=row_dict.get("PostID", ""),
                        persona=row_dict.get("Persona", "MainUser"),
                        content=row_dict.get("Content", ""),
                        content_type=row_dict.get("ContentType", "post"),
                        status=QueueStatus.READY,
                        scheduled_time=row_dict.get("ScheduledTime"),
                        target_url=row_dict.get("TargetURL"),
                        notes=row_dict.get("Notes"),
                        created_at=row_dict.get("CreatedAt"),
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
        """Update the status of a queue item after execution."""
        # Find the Status column index from headers
        rows = self._read_range(f"{TAB_OUTBOUND_QUEUE}!A1:K1")
        if not rows:
            return
        header = rows[0]

        status_col = _col_letter(header.index("Status")) if "Status" in header else "F"
        executed_col = _col_letter(header.index("ExecutedAt")) if "ExecutedAt" in header else "G"
        notes_col = _col_letter(header.index("Notes")) if "Notes" in header else "H"

        row = item.row_index
        self._update_cells(
            f"{TAB_OUTBOUND_QUEUE}!{status_col}{row}",
            [[status.value]],
        )
        self._update_cells(
            f"{TAB_OUTBOUND_QUEUE}!{executed_col}{row}",
            [[datetime.utcnow().isoformat()]],
        )
        if notes:
            self._update_cells(
                f"{TAB_OUTBOUND_QUEUE}!{notes_col}{row}",
                [[notes]],
            )
        logger.info("Updated queue item row %d -> %s", row, status.value)

    # ------------------------------------------------------------------
    # CommentTargets
    # ------------------------------------------------------------------

    def get_comment_targets(self) -> list[CommentTarget]:
        """Read all comment targets from the Sheet."""
        rows = self._read_range(f"{TAB_COMMENT_TARGETS}!A:F")
        if len(rows) < 2:
            return []

        header = rows[0]
        targets = []
        for row in rows[1:]:
            d = dict(zip(header, row + [""] * (len(header) - len(row))))
            targets.append(
                CommentTarget(
                    name=d.get("Name", ""),
                    linkedin_url=d.get("LinkedInURL", ""),
                    category=d.get("Category", "network"),
                    priority=int(d.get("Priority", 1) or 1),
                    last_commented=d.get("LastCommented"),
                    notes=d.get("Notes"),
                )
            )
        return targets

    # ------------------------------------------------------------------
    # CommentTemplates
    # ------------------------------------------------------------------

    def get_comment_templates(self, persona: str = "MainUser") -> list[CommentTemplate]:
        """Read comment templates, optionally filtered by persona."""
        rows = self._read_range(f"{TAB_COMMENT_TEMPLATES}!A:E")
        if len(rows) < 2:
            return []

        header = rows[0]
        templates = []
        for row in rows[1:]:
            d = dict(zip(header, row + [""] * (len(header) - len(row))))
            t = CommentTemplate(
                template_id=d.get("TemplateID", ""),
                category=d.get("Category", ""),
                template_text=d.get("TemplateText", ""),
                persona=d.get("Persona", "MainUser"),
                use_count=int(d.get("UseCount", 0) or 0),
            )
            if persona == "all" or t.persona == persona:
                templates.append(t)
        return templates

    # ------------------------------------------------------------------
    # ReplyRules
    # ------------------------------------------------------------------

    def get_reply_rules(self) -> list[ReplyRule]:
        """Read reply rules (BLOCK/REPLY triggers)."""
        rows = self._read_range(f"{TAB_REPLY_RULES}!A:D")
        if len(rows) < 2:
            return []

        header = rows[0]
        rules = []
        for row in rows[1:]:
            d = dict(zip(header, row + [""] * (len(header) - len(row))))
            rules.append(
                ReplyRule(
                    trigger_phrase=d.get("TriggerPhrase", ""),
                    action=ReplyAction(d.get("Action", "IGNORE")),
                    response_template=d.get("ResponseTemplate"),
                    notes=d.get("Notes"),
                )
            )
        return rules

    # ------------------------------------------------------------------
    # SafetyTerms
    # ------------------------------------------------------------------

    def get_safety_terms(self) -> list[SafetyTerm]:
        """Read all safety terms from the Sheet."""
        rows = self._read_range(f"{TAB_SAFETY_TERMS}!A:C")
        if len(rows) < 2:
            return []

        header = rows[0]
        terms = []
        for row in rows[1:]:
            d = dict(zip(header, row + [""] * (len(header) - len(row))))
            terms.append(
                SafetyTerm(
                    term=d.get("Term", ""),
                    category=d.get("Category", ""),
                    severity=d.get("Severity", "BLOCK"),
                )
            )
        return terms

    # ------------------------------------------------------------------
    # ScheduleControl
    # ------------------------------------------------------------------

    def get_schedule_windows(self) -> list[ScheduleWindow]:
        """Read posting schedule windows."""
        rows = self._read_range(f"{TAB_SCHEDULE_CONTROL}!A:E")
        if len(rows) < 2:
            return []

        header = rows[0]
        windows = []
        for row in rows[1:]:
            d = dict(zip(header, row + [""] * (len(header) - len(row))))
            windows.append(
                ScheduleWindow(
                    day_of_week=d.get("DayOfWeek", ""),
                    window_name=d.get("WindowName", "morning"),
                    start_time=d.get("StartTime", "08:00"),
                    end_time=d.get("EndTime", "11:00"),
                    enabled=d.get("Enabled", "TRUE").upper() == "TRUE",
                )
            )
        return windows

    # ------------------------------------------------------------------
    # EngineControl
    # ------------------------------------------------------------------

    def get_engine_control(self) -> EngineControl:
        """Read current engine settings (mode, phase, toggles)."""
        rows = self._read_range(f"{TAB_ENGINE_CONTROL}!A:B")
        if len(rows) < 2:
            return EngineControl()

        settings = {}
        for row in rows:
            if len(row) >= 2:
                settings[row[0].strip()] = row[1].strip()

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
    # ------------------------------------------------------------------

    def log_action(self, entry: SystemLogEntry) -> None:
        """Append a log entry to SystemLog."""
        self._append_row(
            TAB_SYSTEM_LOG,
            [
                entry.timestamp,
                entry.action,
                entry.persona,
                entry.target,
                entry.status,
                entry.details,
                entry.error or "",
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
        """Convenience wrapper to log an action."""
        self.log_action(
            SystemLogEntry(
                action=action,
                persona=persona,
                target=target,
                status=status,
                details=details,
                error=error,
            )
        )


def _col_letter(index: int) -> str:
    """Convert a 0-based column index to a letter (A, B, ..., Z, AA, ...)."""
    result = ""
    while index >= 0:
        result = chr(65 + index % 26) + result
        index = index // 26 - 1
    return result
