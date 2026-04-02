"""
Pipeline management API routes.

Provides endpoints for triggering pipeline runs and viewing run history.
"""

import asyncio
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from api.deps import DataClientDep, AuthDep

router = APIRouter(prefix="/pipeline", tags=["pipeline"])
logger = logging.getLogger(__name__)


class RunTriggerRequest(BaseModel):
    trigger_type: str = "manual"
    dry_run: bool = False


@router.get("/runs")
async def get_pipeline_runs(
    client: DataClientDep,
    _auth: AuthDep,
    limit: int = 50,
    offset: int = 0,
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
    return {"status": "not_found"}


@router.post("/run")
async def trigger_pipeline_run(
    body: RunTriggerRequest,
    client: DataClientDep,
    _auth: AuthDep,
):
    """Trigger a new pipeline run.

    Creates the run record immediately and returns the ID.
    The actual pipeline execution happens asynchronously.
    """
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
    limit: int = 100,
    offset: int = 0,
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
