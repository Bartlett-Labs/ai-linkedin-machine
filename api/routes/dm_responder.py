"""API routes for the DM auto-responder."""

import asyncio
from typing import Optional

from fastapi import APIRouter

router = APIRouter(tags=["dm-responder"])

_running_task: Optional[asyncio.Task] = None


@router.get("/dm-responder/status")
async def dm_responder_status():
    """Get DM responder status — replied today, queue depth, intent breakdown."""
    from engagement.dm_responder import get_dm_responder_status
    return await get_dm_responder_status()


@router.get("/dm-responder/replies")
async def dm_responder_replies(limit: int = 50, offset: int = 0):
    """Get DM reply history."""
    import json
    import os
    from utils import project_path

    tracker_path = project_path("tracking", "linkedin", "dm_replies.json")
    if not os.path.exists(tracker_path):
        return {"replies": [], "total": 0, "limit": limit, "offset": offset}

    with open(tracker_path, "r") as f:
        tracker = json.load(f)

    replies = tracker.get("replies_sent", [])
    replies.sort(key=lambda r: r.get("sent_at", ""), reverse=True)
    total = len(replies)
    page = replies[offset : offset + limit]
    return {"replies": page, "total": total, "limit": limit, "offset": offset}


@router.get("/dm-responder/queue")
async def dm_responder_queue():
    """Get pending replies waiting to be sent."""
    import json
    import os
    from utils import project_path

    tracker_path = project_path("tracking", "linkedin", "dm_replies.json")
    if not os.path.exists(tracker_path):
        return {"queue": [], "count": 0}

    with open(tracker_path, "r") as f:
        tracker = json.load(f)

    queue = [e for e in tracker.get("reply_queue", []) if not e.get("sent", False)]
    return {"queue": queue, "count": len(queue)}


@router.post("/dm-responder/run")
async def trigger_dm_responder(
    dry_run: bool = False,
    headless: bool = True,
    max_replies: int = 0,
):
    """Trigger a DM scan + reply run."""
    global _running_task

    if _running_task and not _running_task.done():
        return {"status": "already_running"}

    from engagement.dm_responder import run_dm_responder

    async def _run():
        return await run_dm_responder(
            headless=headless,
            dry_run=dry_run,
            max_replies=max_replies,
        )

    _running_task = asyncio.create_task(_run())
    return {"status": "started", "dry_run": dry_run}


@router.delete("/dm-responder/queue/{index}")
async def cancel_queued_reply(index: int):
    """Remove a queued reply before it sends."""
    import json
    import os
    from utils import project_path

    tracker_path = project_path("tracking", "linkedin", "dm_replies.json")
    if not os.path.exists(tracker_path):
        return {"status": "not_found"}

    with open(tracker_path, "r") as f:
        tracker = json.load(f)

    queue = tracker.get("reply_queue", [])
    pending = [e for e in queue if not e.get("sent", False)]

    if index < 0 or index >= len(pending):
        return {"status": "not_found", "index": index, "queue_size": len(pending)}

    removed = pending.pop(index)
    tracker["reply_queue"] = [e for e in queue if e.get("sent", False)] + pending

    with open(tracker_path, "w") as f:
        json.dump(tracker, f, indent=2)

    return {"status": "removed", "sender": removed.get("sender", ""), "intent": removed.get("intent", "")}
