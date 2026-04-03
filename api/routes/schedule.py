"""Schedule and activity window routes."""

from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api.deps import AuthDep, DataClientDep
from scheduling.content_calendar import get_weekly_plan, POSTING_WINDOWS
from db.client import TAB_ACTIVITY_WINDOWS

router = APIRouter(prefix="/schedule", tags=["schedule"])


class ActivityWindowResponse(BaseModel):
    window_name: str
    start_hour: int
    end_hour: int
    days_of_week: str = "all"
    enabled: bool = True


class ActivityWindowCreate(BaseModel):
    window_name: str
    start_hour: int
    end_hour: int
    days_of_week: str = "all"
    enabled: bool = True


class ScheduleConfigResponse(BaseModel):
    mode: str
    posts_per_week: int
    comments_per_day_min: int
    comments_per_day_max: int
    phantom_comments_min: int
    phantom_comments_max: int
    min_delay_sec: int
    max_likes_per_day: int


class ScheduleConfigUpdate(BaseModel):
    posts_per_week: Optional[int] = None
    comments_per_day_min: Optional[int] = None
    comments_per_day_max: Optional[int] = None
    phantom_comments_min: Optional[int] = None
    phantom_comments_max: Optional[int] = None
    min_delay_sec: Optional[int] = None
    max_likes_per_day: Optional[int] = None


class WeeklyPlanDay(BaseModel):
    date: str
    day: str
    is_post_day: bool
    actions: list[dict]


# Column name mappings for ScheduleControl
_SCHEDULE_FIELD_MAP = {
    "posts_per_week": "PostsPerWeek",
    "comments_per_day_min": "CommentsPerDay",
    "min_delay_sec": "MinDelaySec",
    "max_likes_per_day": "MaxLikesPerDay",
}

# ActivityWindows header
_ACTIVITY_HEADER = ["WindowName", "StartHour", "EndHour", "DaysOfWeek", "Enabled"]


@router.get("/windows", response_model=list[ActivityWindowResponse])
def get_activity_windows(client: DataClientDep, _auth: AuthDep):
    """Get all activity windows."""
    windows = client.get_activity_windows()
    if not windows:
        # Return hardcoded defaults
        return [
            ActivityWindowResponse(window_name=name, start_hour=w["start"], end_hour=w["end"])
            for name, w in POSTING_WINDOWS.items()
        ]
    return [
        ActivityWindowResponse(
            window_name=w.window_name,
            start_hour=w.start_hour,
            end_hour=w.end_hour,
            days_of_week=w.days_of_week,
            enabled=w.enabled,
        )
        for w in windows
    ]


@router.post("/windows", response_model=dict)
def create_activity_window(
    body: ActivityWindowCreate,
    client: DataClientDep,
    _auth: AuthDep,
):
    """Add a new activity window."""
    client.append_tab_row(
        TAB_ACTIVITY_WINDOWS,
        _ACTIVITY_HEADER,
        {
            "WindowName": body.window_name,
            "StartHour": str(body.start_hour),
            "EndHour": str(body.end_hour),
            "DaysOfWeek": body.days_of_week,
            "Enabled": "TRUE" if body.enabled else "FALSE",
        },
    )
    return {"status": "created", "window_name": body.window_name}


@router.get("/configs", response_model=list[ScheduleConfigResponse])
def get_schedule_configs(client: DataClientDep, _auth: AuthDep):
    """Get per-phase schedule configurations."""
    configs = client.get_schedule_configs()
    return [
        ScheduleConfigResponse(
            mode=c.mode,
            posts_per_week=c.posts_per_week,
            comments_per_day_min=c.comments_per_day_min,
            comments_per_day_max=c.comments_per_day_max,
            phantom_comments_min=c.phantom_comments_min,
            phantom_comments_max=c.phantom_comments_max,
            min_delay_sec=c.min_delay_sec,
            max_likes_per_day=c.max_likes_per_day,
        )
        for c in configs
    ]


@router.put("/configs/{mode}", response_model=dict)
def update_schedule_config(
    mode: str,
    body: ScheduleConfigUpdate,
    client: DataClientDep,
    _auth: AuthDep,
):
    """Update a schedule config by mode name."""
    updates = {}
    if body.posts_per_week is not None:
        updates["PostsPerWeek"] = str(body.posts_per_week)
    if body.comments_per_day_min is not None and body.comments_per_day_max is not None:
        updates["CommentsPerDay"] = f"{body.comments_per_day_min}-{body.comments_per_day_max}"
    elif body.comments_per_day_min is not None:
        updates["CommentsPerDay"] = str(body.comments_per_day_min)
    if body.phantom_comments_min is not None and body.phantom_comments_max is not None:
        updates["PhantomComments"] = f"{body.phantom_comments_min}-{body.phantom_comments_max}"
    if body.min_delay_sec is not None:
        updates["MinDelaySec"] = str(body.min_delay_sec)
    if body.max_likes_per_day is not None:
        updates["MaxLikesPerDay"] = str(body.max_likes_per_day)

    if updates:
        client.update_schedule_config(mode, updates)

    return {"status": "updated", "mode": mode}


@router.get("/weekly-plan", response_model=list[WeeklyPlanDay])
def get_weekly_plan_route(client: DataClientDep, _auth: AuthDep):
    """Get the current weekly content plan."""
    engine = client.get_engine_control()
    windows = client.get_activity_windows()
    plan = get_weekly_plan(phase=engine.phase.value, schedule_windows=windows or None)
    return [WeeklyPlanDay(**day) for day in plan]
