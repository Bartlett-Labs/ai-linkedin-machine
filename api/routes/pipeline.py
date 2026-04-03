"""
Pipeline management API routes.

Provides endpoints for triggering pipeline runs, viewing run history,
and monitoring errors. Pipeline execution happens asynchronously via
subprocess invocation of main.py.
"""

import asyncio
import logging
import os
import re
import sys
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from api.deps import DataClientDep, AuthDep, get_data_client

router = APIRouter(prefix="/pipeline", tags=["pipeline"])
logger = logging.getLogger(__name__)

# Track running pipeline tasks to prevent GC and enable status checks
_running_tasks: dict[int, asyncio.Task] = {}

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class RunTriggerRequest(BaseModel):
    trigger_type: Literal["manual", "scheduled", "api"] = "manual"
    dry_run: bool = False
    skip_ingest: bool = False
    skip_generate: bool = False
    comments_only: bool = False
    replies_only: bool = False


def _parse_action_counts(output: str) -> dict:
    """Best-effort parsing of action counts from pipeline stdout."""
    counts = {
        "posts_made": 0,
        "comments_made": 0,
        "replies_made": 0,
        "phantom_actions": 0,
    }

    # Look for patterns like "Comments complete: 5 actions"
    for line in output.splitlines():
        line_upper = line.upper()
        if "COMMENT" in line_upper and "COMPLETE" in line_upper:
            m = re.search(r"(\d+)\s*action", line)
            if m:
                counts["comments_made"] = int(m.group(1))
        elif "REPL" in line_upper and "COMPLETE" in line_upper:
            m = re.search(r"(\d+)\s*action", line)
            if m:
                counts["replies_made"] = int(m.group(1))
        elif "PHANTOM" in line_upper:
            m = re.search(r"(\d+)\s*action", line)
            if m:
                counts["phantom_actions"] = int(m.group(1))
        elif "POST" in line_upper and ("MADE" in line_upper or "COMPLETE" in line_upper):
            m = re.search(r"(\d+)", line)
            if m:
                counts["posts_made"] = int(m.group(1))

    return counts


async def _execute_pipeline(run_id: int, body: RunTriggerRequest, client) -> None:
    """Run main.py as a subprocess and update the pipeline run record on completion."""
    python = sys.executable
    cmd = [python, os.path.join(_PROJECT_ROOT, "main.py")]

    if body.dry_run:
        cmd.append("--dry-run")
    if body.skip_ingest:
        cmd.append("--skip-ingest")
    if body.skip_generate:
        cmd.append("--skip-generate")
    if body.comments_only:
        cmd.append("--comments-only")
    if body.replies_only:
        cmd.append("--replies-only")

    logger.info("Pipeline run #%d: executing %s", run_id, " ".join(cmd))

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=_PROJECT_ROOT,
        )

        stdout_bytes, stderr_bytes = await process.communicate()
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        if process.returncode == 0:
            counts = _parse_action_counts(stdout)
            # Keep last 2000 chars of output as summary
            summary = stdout[-2000:] if len(stdout) > 2000 else stdout
            client.complete_pipeline_run(
                run_id,
                status="completed",
                posts_made=counts["posts_made"],
                comments_made=counts["comments_made"],
                replies_made=counts["replies_made"],
                phantom_actions=counts["phantom_actions"],
                summary=summary.strip(),
            )
            logger.info("Pipeline run #%d completed: %s", run_id, counts)
        else:
            error_tail = stderr[-1000:] if len(stderr) > 1000 else stderr
            client.complete_pipeline_run(
                run_id,
                status="failed",
                errors={
                    "exit_code": process.returncode,
                    "stderr": error_tail,
                },
                summary=f"Pipeline failed with exit code {process.returncode}",
            )
            logger.error(
                "Pipeline run #%d failed (exit %d): %s",
                run_id, process.returncode, error_tail[:200],
            )

    except Exception as e:
        logger.exception("Pipeline run #%d crashed: %s", run_id, e)
        client.complete_pipeline_run(
            run_id,
            status="failed",
            errors={"exception": str(e)},
            summary=f"Pipeline crashed: {e}",
        )
    finally:
        _running_tasks.pop(run_id, None)


@router.get("/runs")
async def get_pipeline_runs(
    client: DataClientDep,
    _auth: AuthDep,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Get pipeline run history."""
    runs = client.get_pipeline_runs(limit=limit)
    # Apply offset manually since get_pipeline_runs doesn't support it yet
    sliced = runs[offset:offset + limit] if offset > 0 else runs
    return {
        "runs": sliced,
        "total": len(runs),
        "limit": limit,
        "offset": offset,
    }


@router.get("/runs/{run_id}")
async def get_pipeline_run(
    run_id: int,
    client: DataClientDep,
    _auth: AuthDep,
):
    """Get a single pipeline run by ID."""
    runs = client.get_pipeline_runs(limit=500)
    for run in runs:
        if run["id"] == run_id:
            return run
    raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")


@router.post("/run")
async def trigger_pipeline_run(
    body: RunTriggerRequest,
    client: DataClientDep,
    _auth: AuthDep,
):
    """Trigger a new pipeline run.

    Creates the run record immediately, launches main.py as an async
    subprocess, and returns the run ID. Poll GET /api/pipeline/runs/{id}
    for status updates.
    """
    # Concurrency guard — prevent duplicate runs
    existing = client.get_pipeline_runs(limit=10)
    active = [r for r in existing if r["status"] in ("running", "pending")]
    if active:
        raise HTTPException(
            status_code=409,
            detail=f"Pipeline run #{active[0]['id']} is already {active[0]['status']}",
        )

    engine = client.get_engine_control()
    run_id = client.create_pipeline_run(
        trigger_type=body.trigger_type,
        phase=engine.phase.value,
    )

    logger.info(
        "Pipeline run #%d triggered (type=%s, dry_run=%s, phase=%s)",
        run_id,
        body.trigger_type,
        body.dry_run,
        engine.phase.value,
    )

    # Launch pipeline as background task
    task = asyncio.create_task(_execute_pipeline(run_id, body, client))
    _running_tasks[run_id] = task

    return {
        "status": "triggered",
        "run_id": run_id,
        "phase": engine.phase.value,
        "mode": engine.mode.value,
        "dry_run": body.dry_run,
    }


@router.get("/errors")
async def get_pipeline_errors(
    client: DataClientDep,
    _auth: AuthDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Get aggregated errors from pipeline runs and system logs."""
    # Errors from pipeline runs
    all_runs = client.get_pipeline_runs(limit=200)
    failed_runs = [
        {
            "source": "pipeline",
            "run_id": r["id"],
            "timestamp": r["started_at"],
            "phase": r["phase"],
            "status": r["status"],
            "errors": r["errors"],
            "summary": r["summary"],
        }
        for r in all_runs
        if r["status"] == "failed" or r.get("errors")
    ]

    # Errors from system log
    log_errors, log_total = client.get_error_log(limit=limit, offset=offset)
    system_errors = [
        {
            "source": "system_log",
            "log_id": e["id"],
            "timestamp": e["timestamp"],
            "module": e["module"],
            "action": e["action"],
            "target": e["target"],
            "result": e["result"],
            "notes": e["notes"],
        }
        for e in log_errors
    ]

    return {
        "pipeline_errors": failed_runs,
        "system_errors": system_errors,
        "pipeline_error_count": len(failed_runs),
        "system_error_count": log_total,
    }


@router.websocket("/ws")
async def pipeline_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time pipeline status updates.

    Sends the latest pipeline run status every 5 seconds while a run
    is active, or every 30 seconds when idle. Clients can use this
    to show live progress on the Runs page.
    """
    await websocket.accept()
    logger.info("Pipeline WebSocket connected")
    client = get_data_client()

    try:
        while True:
            runs = client.get_pipeline_runs(limit=5)
            active = [r for r in runs if r["status"] in ("running", "pending")]

            payload = {
                "type": "pipeline_status",
                "active_run": active[0] if active else None,
                "recent_runs": runs[:5],
                "running_task_ids": list(_running_tasks.keys()),
            }
            await websocket.send_json(payload)

            # Poll faster when a run is active
            await asyncio.sleep(5 if active else 30)
    except WebSocketDisconnect:
        logger.info("Pipeline WebSocket disconnected")
    except Exception as e:
        logger.error("Pipeline WebSocket error: %s", e)
