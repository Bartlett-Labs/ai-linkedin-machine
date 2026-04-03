"""History routes — SystemLog browsing with filters and export."""

from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.deps import AuthDep, DataClientDep

router = APIRouter(prefix="/history", tags=["history"])


class HistoryEntry(BaseModel):
    timestamp: str = ""
    module: str = ""
    action: str = ""
    target: str = ""
    result: str = ""
    safety: str = ""
    notes: str = ""


class HistoryResponse(BaseModel):
    entries: list[HistoryEntry]
    total: int
    limit: int
    offset: int


@router.get("", response_model=HistoryResponse)
def get_history(
    client: DataClientDep,
    _auth: AuthDep,
    limit: int = 50,
    offset: int = 0,
    action: Optional[str] = None,
    module: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """Get SystemLog entries with pagination and filtering."""
    entries, total = client.get_system_log(
        limit=limit,
        offset=offset,
        action_filter=action,
        module_filter=module,
        date_from=date_from,
        date_to=date_to,
    )
    return HistoryResponse(
        entries=[
            HistoryEntry(
                timestamp=e.get("Timestamp", ""),
                module=e.get("Module", ""),
                action=e.get("Action", ""),
                target=e.get("Target", ""),
                result=e.get("Result", ""),
                safety=e.get("Safety", ""),
                notes=e.get("Notes", ""),
            )
            for e in entries
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/export")
def export_history_csv(
    client: DataClientDep,
    _auth: AuthDep,
    action: Optional[str] = None,
    module: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """Export SystemLog as CSV."""
    entries, _ = client.get_system_log(
        limit=10000,
        offset=0,
        action_filter=action,
        module_filter=module,
        date_from=date_from,
        date_to=date_to,
    )

    def generate():
        yield "Timestamp,Module,Action,Target,Result,Safety,Notes\n"
        for e in entries:
            row = [
                e.get("Timestamp", ""),
                e.get("Module", ""),
                e.get("Action", ""),
                e.get("Target", "").replace(",", ";"),
                e.get("Result", ""),
                e.get("Safety", ""),
                e.get("Notes", "").replace(",", ";"),
            ]
            yield ",".join(row) + "\n"

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=linkedin-history.csv"},
    )
