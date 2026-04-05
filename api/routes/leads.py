"""Lead tracker API routes — view and manage identified leads."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.deps import AuthDep

router = APIRouter(prefix="/leads", tags=["leads"])
logger = logging.getLogger(__name__)


class Lead(BaseModel):
    name: str
    title: str = ""
    company: str = ""
    score: int = 0
    reasons: list[str] = []
    source_url: str = ""
    interaction_type: str = ""
    comment_preview: str = ""
    discovered_at: str = ""
    status: str = "new"
    interaction_count: int = 1
    last_seen: Optional[str] = None


class LeadUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class LeadsResponse(BaseModel):
    leads: list[Lead]
    total: int


@router.get("", response_model=LeadsResponse)
def get_leads(_auth: AuthDep, status: Optional[str] = None):
    """Get all identified leads, optionally filtered by status."""
    from engagement.lead_tracker import load_leads
    leads = load_leads()

    if status:
        leads = [l for l in leads if l.get("status", "new") == status]

    # Sort by score descending, then by discovered_at descending
    leads.sort(key=lambda l: (-l.get("score", 0), l.get("discovered_at", "")))

    return LeadsResponse(leads=[Lead(**l) for l in leads], total=len(leads))


@router.put("/{lead_name}")
def update_lead(lead_name: str, body: LeadUpdate, _auth: AuthDep):
    """Update a lead's status or add notes."""
    from engagement.lead_tracker import load_leads, save_leads

    leads = load_leads()
    for lead in leads:
        if lead["name"] == lead_name:
            if body.status is not None:
                lead["status"] = body.status
            if body.notes is not None:
                lead["notes"] = body.notes
            save_leads(leads)
            return {"status": "updated", "name": lead_name}

    raise HTTPException(status_code=404, detail=f"Lead '{lead_name}' not found")


@router.delete("/{lead_name}")
def delete_lead(lead_name: str, _auth: AuthDep):
    """Remove a lead from tracking."""
    from engagement.lead_tracker import load_leads, save_leads

    leads = load_leads()
    original_count = len(leads)
    leads = [l for l in leads if l["name"] != lead_name]

    if len(leads) == original_count:
        raise HTTPException(status_code=404, detail=f"Lead '{lead_name}' not found")

    save_leads(leads)
    return {"status": "deleted", "name": lead_name}
