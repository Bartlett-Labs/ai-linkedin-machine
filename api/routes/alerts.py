"""Engagement alerts — WebSocket + REST endpoints for unresponded comments."""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from api.deps import AuthDep, DataClientDep
from api.services.alert_service import AlertManager, EngagementAlert

router = APIRouter(prefix="/alerts", tags=["alerts"])
logger = logging.getLogger(__name__)

# Singleton alert manager
alert_manager = AlertManager()


class AlertResponse(BaseModel):
    alert_id: str
    commenter_name: str
    commenter_url: str = ""
    comment_text: str = ""
    post_url: str = ""
    post_title: str = ""
    discovered_at: str = ""
    elapsed_minutes: float = 0
    urgency: str = "optimal"
    responded: bool = False


@router.get("", response_model=list[AlertResponse])
def get_alerts(_auth: AuthDep, limit: int = 20, unresponded_only: bool = True):
    """Get current engagement alerts."""
    alerts = alert_manager.get_alerts(
        limit=limit,
        unresponded_only=unresponded_only,
    )
    return [
        AlertResponse(
            alert_id=a.alert_id,
            commenter_name=a.commenter_name,
            commenter_url=a.commenter_url,
            comment_text=a.comment_text,
            post_url=a.post_url,
            post_title=a.post_title,
            discovered_at=a.discovered_at,
            elapsed_minutes=a.elapsed_minutes,
            urgency=a.urgency,
            responded=a.responded,
        )
        for a in alerts
    ]


@router.post("/{alert_id}/respond", response_model=dict)
def mark_responded(alert_id: str, _auth: AuthDep):
    """Mark an alert as responded to."""
    alert_manager.mark_responded(alert_id)
    return {"status": "responded", "alert_id": alert_id}


@router.post("/{alert_id}/dismiss", response_model=dict)
def dismiss_alert(alert_id: str, _auth: AuthDep):
    """Dismiss an alert."""
    alert_manager.dismiss(alert_id)
    return {"status": "dismissed", "alert_id": alert_id}


@router.websocket("/ws")
async def alert_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time alert updates.

    Sends alert updates every 30 seconds or when new alerts arrive.
    """
    await websocket.accept()
    logger.info("Alert WebSocket connected")

    try:
        while True:
            alerts = alert_manager.get_alerts(limit=10, unresponded_only=True)
            payload = [
                {
                    "alert_id": a.alert_id,
                    "commenter_name": a.commenter_name,
                    "comment_text": a.comment_text[:100],
                    "post_url": a.post_url,
                    "elapsed_minutes": a.elapsed_minutes,
                    "urgency": a.urgency,
                }
                for a in alerts
            ]
            await websocket.send_json({"type": "alerts", "data": payload})
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        logger.info("Alert WebSocket disconnected")
    except Exception as e:
        logger.error("Alert WebSocket error: %s", e)
