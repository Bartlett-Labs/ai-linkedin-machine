"""
Queue management API routes.

Provides endpoints for viewing, approving, rejecting, and editing
outbound queue items from the dashboard.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from api.deps import DataClientDep, AuthDep

router = APIRouter(prefix="/queue", tags=["queue"])


class QueueUpdateRequest(BaseModel):
    status: Optional[str] = None
    draft_text: Optional[str] = None
    notes: Optional[str] = None
    persona: Optional[str] = None
    target_url: Optional[str] = None
    action_type: Optional[str] = None


class QueueCreateRequest(BaseModel):
    post_id: str = ""
    persona: str = "MainUser"
    draft_text: str
    action_type: str = "post"
    target_url: str = ""
    notes: str = ""


@router.get("")
async def get_queue(
    client: DataClientDep,
    _auth: AuthDep,
    status: str = "",
    limit: int = 100,
    offset: int = 0,
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
        return {"status": "not_found"}
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
    return {"status": "created", "id": new_id}
