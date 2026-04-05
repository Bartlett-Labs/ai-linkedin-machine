"""API routes for the auto-connection engine."""

import asyncio
from typing import Optional

from fastapi import APIRouter, BackgroundTasks

router = APIRouter(tags=["connector"])

# Track running connector tasks
_running_task: Optional[asyncio.Task] = None


@router.get("/connector/status")
async def connector_status():
    """Get current connector status — daily counts, budget, config."""
    from engagement.connector import get_connector_status
    return await get_connector_status()


@router.get("/connector/requests")
async def connector_requests(
    source: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Get connection request history with optional source filter."""
    import json
    import os
    from utils import project_path

    tracker_path = project_path("tracking", "linkedin", "connections.json")
    if not os.path.exists(tracker_path):
        return {"requests": [], "total": 0, "limit": limit, "offset": offset}

    with open(tracker_path, "r") as f:
        tracker = json.load(f)

    requests = tracker.get("requests_sent", [])

    # Filter by source
    if source:
        requests = [r for r in requests if r.get("source") == source]

    # Sort by timestamp descending (newest first)
    requests.sort(key=lambda r: r.get("timestamp", ""), reverse=True)

    total = len(requests)
    page = requests[offset : offset + limit]

    return {"requests": page, "total": total, "limit": limit, "offset": offset}


@router.post("/connector/run")
async def trigger_connector(
    background_tasks: BackgroundTasks,
    dry_run: bool = False,
    commenter_only: bool = False,
    outbound_only: bool = False,
    headless: bool = True,
):
    """Trigger a connection run in the background."""
    global _running_task

    if _running_task and not _running_task.done():
        return {"status": "already_running", "message": "A connector run is already in progress"}

    from engagement.connector import run_connector

    async def _run():
        return await run_connector(
            headless=headless,
            dry_run=dry_run,
            commenter_only=commenter_only,
            outbound_only=outbound_only,
        )

    _running_task = asyncio.create_task(_run())

    return {
        "status": "started",
        "dry_run": dry_run,
        "commenter_only": commenter_only,
        "outbound_only": outbound_only,
    }


@router.get("/connector/acceptances")
async def connector_acceptances():
    """Get recent connection acceptances that may need voice follow-up."""
    import json
    import os
    from utils import project_path

    tracker_path = project_path("tracking", "linkedin", "connections.json")
    if not os.path.exists(tracker_path):
        return {"acceptances": [], "pending_voice": 0, "voice_sent": 0}

    with open(tracker_path, "r") as f:
        tracker = json.load(f)

    voice_sent = tracker.get("voice_sent", [])
    voice_sent_urls = {v.get("profile_url", "").rstrip("/").split("?")[0] for v in voice_sent}

    # Find requests that haven't had voice follow-up yet
    requests = tracker.get("requests_sent", [])
    pending = [
        r for r in requests
        if not r.get("dry_run", False)
        and r.get("profile_url", "").rstrip("/").split("?")[0] not in voice_sent_urls
    ]

    return {
        "pending_voice": len(pending),
        "voice_sent": len(voice_sent),
        "recent_voice": voice_sent[-10:] if voice_sent else [],
    }


@router.get("/connector/voice-queue")
async def voice_queue():
    """Get pending voice messages and recent sends."""
    import json
    import os
    from utils import project_path

    tracker_path = project_path("tracking", "linkedin", "connections.json")
    if not os.path.exists(tracker_path):
        return {"pending": [], "sent": [], "total_sent": 0}

    with open(tracker_path, "r") as f:
        tracker = json.load(f)

    voice_sent = tracker.get("voice_sent", [])
    voice_sent_urls = {v.get("profile_url", "").rstrip("/").split("?")[0] for v in voice_sent}

    # Pending = sent requests without voice follow-up
    requests = tracker.get("requests_sent", [])
    pending = [
        {
            "name": r.get("name", ""),
            "profile_url": r.get("profile_url", ""),
            "headline": r.get("headline", ""),
            "source": r.get("source", ""),
            "sent_at": r.get("timestamp", ""),
        }
        for r in requests
        if not r.get("dry_run", False)
        and r.get("profile_url", "").rstrip("/").split("?")[0] not in voice_sent_urls
    ]

    return {
        "pending": pending[-20:],
        "sent": voice_sent[-20:],
        "total_sent": len(voice_sent),
    }


@router.post("/connector/voice-run")
async def trigger_voice_outreach(
    dry_run: bool = False,
    headless: bool = True,
    max_messages: int = 10,
):
    """Trigger voice outreach for accepted connections."""
    from engagement.voice_outreach import monitor_and_send_voice

    async def _run():
        return await monitor_and_send_voice(
            headless=headless,
            dry_run=dry_run,
            max_messages=max_messages,
        )

    task = asyncio.create_task(_run())

    return {
        "status": "started",
        "dry_run": dry_run,
        "max_messages": max_messages,
    }


@router.get("/connector/config")
async def get_connector_config():
    """Get current connector configuration."""
    import yaml
    from utils import project_path

    config_path = project_path("config", "connector.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


@router.put("/connector/config")
async def update_connector_config(updates: dict):
    """Update connector configuration (partial merge)."""
    import yaml
    from utils import project_path

    config_path = project_path("config", "connector.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Deep merge updates
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(config.get(key), dict):
            config[key].update(value)
        else:
            config[key] = value

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    return config
