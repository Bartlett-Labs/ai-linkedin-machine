"""
LinkedIn Webhook Service — receives real-time social action notifications.

Separate FastAPI microservice on port 3847, behind Cloudflare tunnel at
webhooks.bartlettlabs.io. Shares the db/ module with the main API.

Endpoints:
  GET  /  — LinkedIn challenge-response validation (HMAC-SHA256)
  POST /  — Receive batched social action notifications
"""

import hashlib
import hmac
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so db/ imports work
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
os.chdir(_PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from db.client import DatabaseClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("webhook")

app = FastAPI(
    title="LinkedIn Webhook Service",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

# Shared database client
_db = DatabaseClient()

# Config from environment
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
ORG_URN = os.getenv("LINKEDIN_ORG_URN", "")


# --------------------------------------------------------------------------
# GET / — LinkedIn challenge-response validation
# --------------------------------------------------------------------------

@app.get("/")
async def validate_webhook(challengeCode: str):
    """Respond to LinkedIn's webhook validation challenge.

    LinkedIn sends a GET with ?challengeCode=<uuid>. We must return:
    {
      "challengeCode": "<same uuid>",
      "challengeResponse": "<hex HMAC-SHA256(challengeCode, clientSecret)>"
    }
    with Content-Type: application/json and 200 OK within 3 seconds.
    """
    if not CLIENT_SECRET:
        logger.error("LINKEDIN_CLIENT_SECRET not set — cannot validate webhook")
        return JSONResponse(
            status_code=500,
            content={"error": "Webhook secret not configured"},
        )

    challenge_response = hmac.new(
        CLIENT_SECRET.encode("utf-8"),
        challengeCode.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    logger.info("Webhook validation challenge received — responding with HMAC")

    return JSONResponse(
        content={
            "challengeCode": challengeCode,
            "challengeResponse": challenge_response,
        },
        headers={"content-type": "application/json"},
    )


# --------------------------------------------------------------------------
# POST / — Receive social action notifications
# --------------------------------------------------------------------------

@app.post("/")
async def receive_notification(request: Request):
    """Process LinkedIn social action notification batch.

    LinkedIn batches up to 10 notifications per request. Each contains:
    - action: COMMENT | SHARE | SHARE_MENTION | LIKE
    - generatedActivity: URN of the generated activity
    - organizationalEntity: URN of the org page
    - notificationId: unique ID for deduplication
    - decoratedGeneratedActivity: (optional) enriched payload with comment text

    We must return 200 within 3 seconds or LinkedIn will retry.
    """
    try:
        payload = await request.json()
    except Exception:
        logger.warning("Failed to parse webhook payload")
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    event_type = payload.get("type", "UNKNOWN")
    notifications = payload.get("notifications", [])

    logger.info(
        "Webhook received: type=%s, notifications=%d",
        event_type, len(notifications),
    )

    created_count = 0
    duplicate_count = 0
    queued_count = 0

    for notif in notifications:
        notification_id = notif.get("notificationId")
        if notification_id is None:
            logger.warning("Notification missing notificationId, skipping")
            continue

        # Deduplication — skip if already received
        existing = _db.get_webhook_event_by_notification_id(notification_id)
        if existing:
            duplicate_count += 1
            logger.debug("Duplicate notification %d, skipping", notification_id)
            continue

        action = notif.get("action", "UNKNOWN")
        org_urn = notif.get("organizationalEntity", "")
        generated_urn = notif.get("generatedActivity", "")
        actor_urn = notif.get("actor", "")

        # Extract comment text from decorated payload if present
        comment_text = None
        decorated = notif.get("decoratedGeneratedActivity", {})
        if decorated and isinstance(decorated, dict):
            comment_obj = decorated.get("comment", {})
            if comment_obj and isinstance(comment_obj, dict):
                comment_text = comment_obj.get("text", "")

        # Store the event
        event_data = {
            "event_type": event_type,
            "action": action,
            "notification_id": notification_id,
            "organization_urn": org_urn,
            "generated_activity_urn": generated_urn,
            "actor_urn": actor_urn,
            "comment_text": comment_text,
            "raw_payload": notif,
        }

        event_id = _db.create_webhook_event(event_data)
        created_count += 1
        logger.info(
            "Stored webhook event #%d: action=%s, notification_id=%d",
            event_id, action, notification_id,
        )

        # Auto-queue reply for COMMENT actions
        if action == "COMMENT" and comment_text:
            queue_item_id = _db.add_to_queue(
                post_id=generated_urn,
                persona="MainUser",
                content=f"[Auto-draft reply to webhook comment]\n\nOriginal comment: {comment_text}",
                content_type="reply",
                target_url="",
                notes=f"Auto-queued from webhook event #{event_id} (notification {notification_id})",
            )
            # Link the queue item back to the event
            _db.update_webhook_event_queue_link(event_id, queue_item_id)
            queued_count += 1
            logger.info(
                "Auto-queued reply (queue #%d) for comment on %s",
                queue_item_id, generated_urn,
            )

        # Log to system audit trail
        _db.log(
            action=f"webhook_{action.lower()}",
            target=generated_urn,
            module="webhook",
            status="OK",
            notes=f"notification_id={notification_id}, event_id={event_id}",
        )

    logger.info(
        "Webhook batch processed: %d created, %d duplicates, %d queued",
        created_count, duplicate_count, queued_count,
    )

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "created": created_count,
            "duplicates": duplicate_count,
            "queued": queued_count,
        },
    )


# --------------------------------------------------------------------------
# Health check
# --------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "service": "linkedin-webhook"}


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "webhook.server:app",
        host="0.0.0.0",
        port=int(os.getenv("WEBHOOK_PORT", "3847")),
        reload=True,
    )
