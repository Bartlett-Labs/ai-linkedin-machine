"""Heartbeat scheduler API routes — per-persona autonomous engagement control."""

import asyncio
import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from api.deps import AuthDep, load_personas_config, save_personas_config

router = APIRouter(prefix="/heartbeat", tags=["heartbeat"])
logger = logging.getLogger(__name__)

DEFAULT_SESSION_DIR = os.path.expanduser("~/.ai-linkedin-machine/sessions")

# Track running heartbeat tasks
_running_heartbeats: dict[str, asyncio.Task] = {}


class PersonaHeartbeatStatus(BaseModel):
    name: str
    display_name: str
    has_active_session: bool
    in_active_hours: bool
    active_hours: Optional[dict] = None
    schedule: Optional[dict] = None
    daily_stats: Optional[dict] = None
    is_running: bool = False


class ScheduleUpdate(BaseModel):
    comments_per_cycle: Optional[int] = None
    post_chance_per_cycle: Optional[float] = None
    kyle_comment_chance: Optional[float] = None
    cycle_interval_minutes: Optional[int] = None


class HeartbeatTrigger(BaseModel):
    dry_run: bool = False
    headless: bool = True


def _has_active_session(persona_name: str) -> bool:
    """Check if a persona has a saved browser session."""
    safe_name = persona_name.lower().replace(" ", "_")
    session_path = os.path.join(DEFAULT_SESSION_DIR, safe_name)
    if not os.path.isdir(session_path):
        return False
    return len(os.listdir(session_path)) > 0


def _is_in_active_hours(persona: dict) -> bool:
    """Check if the current time is within the persona's active hours."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    active_hours = persona.get("active_hours")
    if not active_hours:
        return True

    tz = ZoneInfo(active_hours["timezone"])
    now = datetime.now(tz)
    start_h, start_m = map(int, active_hours["start"].split(":"))
    end_h, end_m = map(int, active_hours["end"].split(":"))

    start_minutes = start_h * 60 + start_m
    end_minutes = end_h * 60 + end_m
    now_minutes = now.hour * 60 + now.minute

    return start_minutes <= now_minutes <= end_minutes


def _get_daily_stats_for_persona(persona_name: str) -> dict:
    """Get today's stats for a specific persona."""
    try:
        from engagement.tracker import get_daily_stats
        stats = get_daily_stats(persona=persona_name)
        # Remove non-serializable set
        stats.pop("commented_urls", None)
        return stats
    except Exception as e:
        logger.error("Failed to get daily stats for %s: %s", persona_name, e)
        return {"comments_posted": 0, "posts_made": 0, "replies_sent": 0, "likes_given": 0}


@router.get("/status", response_model=list[PersonaHeartbeatStatus])
def get_heartbeat_status(_auth: AuthDep):
    """Get heartbeat status for all phantom personas."""
    personas = load_personas_config()
    result = []

    for p in personas:
        if p["name"] == "MainUser":
            continue

        name = p["name"]
        result.append(PersonaHeartbeatStatus(
            name=name,
            display_name=p.get("display_name", name),
            has_active_session=_has_active_session(name),
            in_active_hours=_is_in_active_hours(p),
            active_hours=p.get("active_hours"),
            schedule=p.get("schedule"),
            daily_stats=_get_daily_stats_for_persona(name),
            is_running=name in _running_heartbeats and not _running_heartbeats[name].done(),
        ))

    return result


@router.get("/schedule/{persona_name}")
def get_persona_schedule(persona_name: str, _auth: AuthDep):
    """Get schedule config for a specific persona."""
    personas = load_personas_config()
    for p in personas:
        if p["name"].lower() == persona_name.lower():
            return {
                "name": p["name"],
                "display_name": p.get("display_name", p["name"]),
                "schedule": p.get("schedule", {}),
                "active_hours": p.get("active_hours", {}),
                "behavior": p.get("behavior", {}),
            }
    raise HTTPException(status_code=404, detail=f"Persona '{persona_name}' not found")


@router.put("/schedule/{persona_name}")
def update_persona_schedule(
    persona_name: str,
    body: ScheduleUpdate,
    _auth: AuthDep,
):
    """Update schedule config for a specific persona."""
    personas = load_personas_config()
    for p in personas:
        if p["name"].lower() == persona_name.lower():
            schedule = p.setdefault("schedule", {})
            if body.comments_per_cycle is not None:
                schedule["comments_per_cycle"] = body.comments_per_cycle
            if body.post_chance_per_cycle is not None:
                schedule["post_chance_per_cycle"] = body.post_chance_per_cycle
            if body.kyle_comment_chance is not None:
                schedule["kyle_comment_chance"] = body.kyle_comment_chance
            if body.cycle_interval_minutes is not None:
                schedule["cycle_interval_minutes"] = body.cycle_interval_minutes
            save_personas_config(personas)
            return {"status": "updated", "name": persona_name, "schedule": schedule}
    raise HTTPException(status_code=404, detail=f"Persona '{persona_name}' not found")


@router.post("/run/{persona_name}")
async def trigger_heartbeat(
    persona_name: str,
    body: HeartbeatTrigger,
    _auth: AuthDep,
):
    """Trigger a heartbeat cycle for a specific persona."""
    personas = load_personas_config()
    persona = next((p for p in personas if p["name"].lower() == persona_name.lower()), None)
    if not persona:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_name}' not found")

    actual_name = persona["name"]
    if actual_name in _running_heartbeats and not _running_heartbeats[actual_name].done():
        raise HTTPException(status_code=409, detail=f"Heartbeat for '{actual_name}' is already running")

    if not _has_active_session(actual_name):
        raise HTTPException(status_code=400, detail=f"'{persona.get('display_name', actual_name)}' has no active browser session")

    async def _run():
        try:
            from scheduling.heartbeat import run_persona_heartbeat
            result = await run_persona_heartbeat(
                persona_name=actual_name,
                dry_run=body.dry_run,
                headless=body.headless,
            )
            logger.info("Heartbeat completed for %s: %s", actual_name, result)
        except Exception as e:
            logger.error("Heartbeat failed for %s: %s", actual_name, e)
        finally:
            _running_heartbeats.pop(actual_name, None)

    task = asyncio.create_task(_run())
    _running_heartbeats[actual_name] = task

    return {
        "status": "triggered",
        "persona": actual_name,
        "display_name": persona.get("display_name", actual_name),
        "dry_run": body.dry_run,
    }


@router.post("/run-all")
async def trigger_all_heartbeats(body: HeartbeatTrigger, _auth: AuthDep):
    """Trigger heartbeats for all eligible personas."""
    personas = load_personas_config()
    triggered = []
    skipped = []

    for p in personas:
        if p["name"] == "MainUser":
            continue
        name = p["name"]
        display = p.get("display_name", name)

        if name in _running_heartbeats and not _running_heartbeats[name].done():
            skipped.append({"name": name, "display_name": display, "reason": "already running"})
            continue
        if not _has_active_session(name):
            skipped.append({"name": name, "display_name": display, "reason": "no session"})
            continue
        if not _is_in_active_hours(p):
            skipped.append({"name": name, "display_name": display, "reason": "outside active hours"})
            continue

        async def _run(persona_name=name):
            try:
                from scheduling.heartbeat import run_persona_heartbeat
                await run_persona_heartbeat(
                    persona_name=persona_name,
                    dry_run=body.dry_run,
                    headless=body.headless,
                )
            except Exception as e:
                logger.error("Heartbeat failed for %s: %s", persona_name, e)
            finally:
                _running_heartbeats.pop(persona_name, None)

        task = asyncio.create_task(_run())
        _running_heartbeats[name] = task
        triggered.append({"name": name, "display_name": display})

    return {
        "status": "triggered",
        "triggered": triggered,
        "skipped": skipped,
        "dry_run": body.dry_run,
    }
