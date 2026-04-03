"""
Queue management API routes.

Provides endpoints for viewing, approving, rejecting, and editing
outbound queue items from the dashboard.
"""

import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.deps import DataClientDep, AuthDep

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/queue", tags=["queue"])

ValidStatus = Literal["READY", "IN_PROGRESS", "DONE", "FAILED", "SKIPPED"]
ValidPersona = Literal[
    "MainUser", "Marcus Chen", "Dr. Priya Nair",
    "Jake Morrison", "Rebecca Torres", "Alex Kim", "David Okafor",
]
ValidActionType = Literal["post", "comment", "reply", "repost"]


class QueueUpdateRequest(BaseModel):
    status: Optional[ValidStatus] = None
    draft_text: Optional[str] = Field(None, max_length=10000)
    notes: Optional[str] = Field(None, max_length=2000)
    persona: Optional[ValidPersona] = None
    target_url: Optional[str] = Field(None, max_length=2000)
    action_type: Optional[ValidActionType] = None


class QueueCreateRequest(BaseModel):
    post_id: str = ""
    persona: ValidPersona = "MainUser"
    draft_text: str = Field(..., min_length=1, max_length=10000)
    action_type: ValidActionType = "post"
    target_url: str = Field("", max_length=2000)
    notes: str = Field("", max_length=2000)


@router.get("")
async def get_queue(
    client: DataClientDep,
    _auth: AuthDep,
    status: str = "",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """List queue items with optional status filter and pagination."""
    items, total = client.get_queue_items(
        status_filter=status,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/stats")
async def get_queue_stats(
    client: DataClientDep,
    _auth: AuthDep,
):
    """Get queue item counts grouped by status."""
    return client.get_queue_stats()


@router.put("/{item_id}")
async def update_queue_item(
    item_id: int,
    body: QueueUpdateRequest,
    client: DataClientDep,
    _auth: AuthDep,
):
    """Update a queue item (approve, reject, edit)."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return {"status": "no_changes"}

    result = client.update_queue_item(item_id, updates)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Queue item {item_id} not found")
    logger.info("Queue item #%d updated: %s", item_id, list(updates.keys()))
    return {"status": "updated", **result}


@router.post("")
async def create_queue_item(
    body: QueueCreateRequest,
    client: DataClientDep,
    _auth: AuthDep,
):
    """Add a new item to the outbound queue."""
    new_id = client.add_to_queue(
        post_id=body.post_id,
        persona=body.persona,
        content=body.draft_text,
        content_type=body.action_type,
        target_url=body.target_url,
        notes=body.notes,
    )
    logger.info("Queue item #%d created (type=%s, persona=%s)", new_id, body.action_type, body.persona)
    return {"status": "created", "id": new_id}
