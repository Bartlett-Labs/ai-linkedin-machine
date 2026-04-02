"""
Feed source management API routes.

Provides CRUD endpoints for RSS feed sources, replacing config/feeds.json.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from api.deps import DataClientDep, AuthDep

router = APIRouter(prefix="/feeds", tags=["feeds"])


class FeedCreateRequest(BaseModel):
    name: str
    url: str
    type: str = "rss"
    category: str = ""
    active: bool = True


class FeedUpdateRequest(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
    active: Optional[bool] = None


@router.get("")
async def get_feeds(
    client: DataClientDep,
    _auth: AuthDep,
    active_only: bool = False,
):
    """List all feed sources."""
    feeds = client.get_feed_sources(active_only=active_only)
    return {"feeds": feeds, "total": len(feeds)}


@router.post("")
async def create_feed(
    body: FeedCreateRequest,
    client: DataClientDep,
    _auth: AuthDep,
):
    """Create a new feed source."""
    new_id = client.create_feed_source(
        name=body.name,
        url=body.url,
        feed_type=body.type,
        category=body.category,
        active=body.active,
    )
    return {"status": "created", "id": new_id}


@router.put("/{feed_id}")
async def update_feed(
    feed_id: int,
    body: FeedUpdateRequest,
    client: DataClientDep,
    _auth: AuthDep,
):
    """Update a feed source."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return {"status": "no_changes"}

    found = client.update_feed_source(feed_id, updates)
    if not found:
        return {"status": "not_found"}
    return {"status": "updated", "id": feed_id}


@router.delete("/{feed_id}")
async def delete_feed(
    feed_id: int,
    client: DataClientDep,
    _auth: AuthDep,
):
    """Delete a feed source."""
    found = client.delete_feed_source(feed_id)
    if not found:
        return {"status": "not_found"}
    return {"status": "deleted", "id": feed_id}
