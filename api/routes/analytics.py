"""Analytics routes — post/comment performance, trends."""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api.deps import AuthDep, DataClientDep
from api.services.analytics_service import (
    get_daily_summary,
    get_engagement_trends,
    get_per_persona_stats,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


class DailySummary(BaseModel):
    date: str
    comments_posted: int = 0
    posts_made: int = 0
    replies_sent: int = 0
    likes_given: int = 0
    last_action_time: Optional[str] = None


class EngagementTrend(BaseModel):
    date: str
    comments: int = 0
    posts: int = 0
    replies: int = 0
    likes: int = 0


class PersonaStats(BaseModel):
    persona: str
    total_actions: int = 0
    comments: int = 0
    posts: int = 0
    replies: int = 0


@router.get("/today", response_model=DailySummary)
def get_today_summary(_auth: AuthDep):
    """Get today's activity summary from the local tracker."""
    summary = get_daily_summary()
    return DailySummary(**summary)


@router.get("/trends", response_model=list[EngagementTrend])
def get_trends(
    client: DataClientDep,
    _auth: AuthDep,
    days: int = 30,
):
    """Get engagement trends over the last N days."""
    trends = get_engagement_trends(client, days=days)
    return [EngagementTrend(**t) for t in trends]


@router.get("/personas", response_model=list[PersonaStats])
def get_persona_analytics(
    client: DataClientDep,
    _auth: AuthDep,
    days: int = 30,
):
    """Get per-persona activity breakdown."""
    stats = get_per_persona_stats(client, days=days)
    return [PersonaStats(**s) for s in stats]
