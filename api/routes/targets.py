"""Comment targets CRUD routes."""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api.deps import AuthDep, SheetsClientDep
from sheets.client import TAB_COMMENT_TARGETS

router = APIRouter(prefix="/targets", tags=["targets"])

_TARGETS_HEADER = ["ID", "Name", "LinkedInURL", "Category", "Priority", "LastCommentDate", "Notes"]


class CommentTargetResponse(BaseModel):
    name: str
    linkedin_url: str
    category: str = "network"
    priority: int = 1
    last_comment_date: Optional[str] = None
    notes: Optional[str] = None


class CommentTargetCreate(BaseModel):
    name: str
    linkedin_url: str
    category: str = "network"
    priority: int = 1
    notes: Optional[str] = None


class CommentTargetUpdate(BaseModel):
    name: Optional[str] = None
    linkedin_url: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = None
    notes: Optional[str] = None


@router.get("", response_model=list[CommentTargetResponse])
def get_comment_targets(
    sheets: SheetsClientDep,
    _auth: AuthDep,
    category: Optional[str] = None,
):
    """Get all comment targets, optionally filtered by category."""
    targets = sheets.get_comment_targets()
    if category:
        targets = [t for t in targets if t.category.lower() == category.lower()]
    return [
        CommentTargetResponse(
            name=t.name,
            linkedin_url=t.linkedin_url,
            category=t.category,
            priority=t.priority,
            last_comment_date=t.last_comment_date,
            notes=t.notes,
        )
        for t in targets
    ]


@router.post("", response_model=dict)
def create_comment_target(
    body: CommentTargetCreate,
    sheets: SheetsClientDep,
    _auth: AuthDep,
):
    """Add a new comment target."""
    existing = sheets.get_comment_targets()
    next_id = len(existing) + 1

    sheets.append_tab_row(
        TAB_COMMENT_TARGETS,
        _TARGETS_HEADER,
        {
            "ID": str(next_id),
            "Name": body.name,
            "LinkedInURL": body.linkedin_url,
            "Category": body.category,
            "Priority": str(body.priority),
            "LastCommentDate": "",
            "Notes": body.notes or "",
        },
    )
    return {"status": "created", "name": body.name}


@router.put("/{target_name}", response_model=dict)
def update_comment_target(
    target_name: str,
    body: CommentTargetUpdate,
    sheets: SheetsClientDep,
    _auth: AuthDep,
):
    """Update a comment target by name."""
    header, data, _ = sheets.get_tab_data(TAB_COMMENT_TARGETS, "A:G")
    for row in data:
        row_idx = int(row[0])
        row_dict = dict(zip(header, row[1:]))
        if row_dict.get("Name", "").strip().lower() == target_name.lower():
            updates = {}
            if body.name is not None:
                updates["Name"] = body.name
            if body.linkedin_url is not None:
                updates["LinkedInURL"] = body.linkedin_url
            if body.category is not None:
                updates["Category"] = body.category
            if body.priority is not None:
                updates["Priority"] = str(body.priority)
            if body.notes is not None:
                updates["Notes"] = body.notes
            sheets.update_tab_row(TAB_COMMENT_TARGETS, row_idx, header, updates)
            return {"status": "updated", "name": target_name}

    return {"status": "not_found", "name": target_name}


@router.delete("/{target_name}", response_model=dict)
def delete_comment_target(
    target_name: str,
    sheets: SheetsClientDep,
    _auth: AuthDep,
):
    """Delete a comment target by name."""
    header, data, _ = sheets.get_tab_data(TAB_COMMENT_TARGETS, "A:G")
    for row in data:
        row_idx = int(row[0])
        row_dict = dict(zip(header, row[1:]))
        if row_dict.get("Name", "").strip().lower() == target_name.lower():
            sheets.delete_tab_row(TAB_COMMENT_TARGETS, row_idx, len(header))
            return {"status": "deleted", "name": target_name}
    return {"status": "not_found", "name": target_name}
