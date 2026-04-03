"""
Feed source management API routes.

Provides CRUD endpoints for RSS feed sources, replacing config/feeds.json.
"""

import logging
import re
from typing import Literal, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from api.deps import DataClientDep, AuthDep

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feeds", tags=["feeds"])

ValidFeedType = Literal["rss", "atom", "json", "scraper"]
ValidCategory = Literal[
    "ai", "ai_automation", "automation", "ops", "ops_efficiency",
    "tech", "tech_news", "business", "career", "research",
    "dev_tools", "personal_growth", "builder_stories", "",
]

_PRIVATE_IP_PATTERNS = [
    re.compile(r"^127\."),
    re.compile(r"^10\."),
    re.compile(r"^172\.(1[6-9]|2\d|3[01])\."),
    re.compile(r"^192\.168\."),
    re.compile(r"^169\.254\."),
    re.compile(r"^0\."),
]
_PRIVATE_HOSTS = {"localhost", "0.0.0.0", "[::]", "[::1]"}


def _validate_feed_url(url: str) -> str:
    """Reject URLs pointing to private/internal network addresses (SSRF protection)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must use http or https scheme")
    hostname = (parsed.hostname or "").lower()
    if hostname in _PRIVATE_HOSTS:
        raise ValueError("URL must not point to localhost or internal addresses")
    for pattern in _PRIVATE_IP_PATTERNS:
        if pattern.match(hostname):
            raise ValueError("URL must not point to private IP ranges")
    return url


class FeedCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    url: str = Field(..., min_length=1, max_length=2000)
    type: ValidFeedType = "rss"
    category: ValidCategory = ""
    active: bool = True

    @field_validator("url")
    @classmethod
    def check_url(cls, v: str) -> str:
        return _validate_feed_url(v)


class FeedUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    url: Optional[str] = Field(None, min_length=1, max_length=2000)
    type: Optional[ValidFeedType] = None
    category: Optional[ValidCategory] = None
    active: Optional[bool] = None

    @field_validator("url")
    @classmethod
    def check_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_feed_url(v)
        return v


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
    logger.info("Feed source #%d created: %s (%s)", new_id, body.name, body.url)
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
        raise HTTPException(status_code=404, detail=f"Feed source {feed_id} not found")
    logger.info("Feed source #%d updated: %s", feed_id, list(updates.keys()))
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
        raise HTTPException(status_code=404, detail=f"Feed source {feed_id} not found")
    logger.info("Feed source #%d deleted", feed_id)
    return {"status": "deleted", "id": feed_id}
