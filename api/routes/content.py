"""Content bank and repost bank CRUD routes."""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api.deps import AuthDep, SheetsClientDep
from sheets.client import TAB_CONTENT_BANK, TAB_REPOST_BANK

router = APIRouter(prefix="/content", tags=["content"])

_CONTENT_HEADER = ["ID", "Category", "PostType", "Draft", "SafetyFlag", "Ready", "LastUsed", "Notes"]
_REPOST_HEADER = ["ID", "SourceName", "SourceURL", "Summary", "CommentaryPrompt", "SafetyFlag", "LastUsed", "Notes"]


class ContentBankItemResponse(BaseModel):
    item_id: int = 0
    category: str = ""
    post_type: str = ""
    draft: str = ""
    safety_flag: int = 0
    ready: bool = True
    last_used: Optional[str] = None
    notes: Optional[str] = None


class ContentBankItemCreate(BaseModel):
    category: str
    post_type: str = "Original"
    draft: str
    safety_flag: int = 0
    ready: bool = True
    notes: Optional[str] = None


class ContentBankItemUpdate(BaseModel):
    category: Optional[str] = None
    post_type: Optional[str] = None
    draft: Optional[str] = None
    safety_flag: Optional[int] = None
    ready: Optional[bool] = None
    notes: Optional[str] = None


class RepostBankItemResponse(BaseModel):
    item_id: int = 0
    source_name: str = ""
    source_url: str = ""
    summary: str = ""
    commentary_prompt: str = ""
    safety_flag: int = 0
    last_used: Optional[str] = None
    notes: Optional[str] = None


class RepostBankItemCreate(BaseModel):
    source_name: str
    source_url: str
    summary: str = ""
    commentary_prompt: str = ""
    safety_flag: int = 0
    notes: Optional[str] = None


# ------------------------------------------------------------------
# Content Bank
# ------------------------------------------------------------------

@router.get("/bank", response_model=list[ContentBankItemResponse])
def get_content_bank(
    sheets: SheetsClientDep,
    _auth: AuthDep,
    ready_only: bool = False,
):
    """Get all content bank items."""
    items = sheets.get_content_bank(ready_only=ready_only)
    return [
        ContentBankItemResponse(
            item_id=i.item_id,
            category=i.category,
            post_type=i.post_type,
            draft=i.draft,
            safety_flag=i.safety_flag,
            ready=i.ready,
            last_used=i.last_used,
            notes=i.notes,
        )
        for i in items
    ]


@router.post("/bank", response_model=dict)
def create_content_bank_item(
    body: ContentBankItemCreate,
    sheets: SheetsClientDep,
    _auth: AuthDep,
):
    """Add a new content bank item."""
    # Get next ID
    existing = sheets.get_content_bank(ready_only=False)
    next_id = max((i.item_id for i in existing), default=0) + 1

    sheets.append_tab_row(
        TAB_CONTENT_BANK,
        _CONTENT_HEADER,
        {
            "ID": str(next_id),
            "Category": body.category,
            "PostType": body.post_type,
            "Draft": body.draft,
            "SafetyFlag": str(body.safety_flag),
            "Ready": "TRUE" if body.ready else "FALSE",
            "LastUsed": "",
            "Notes": body.notes or "",
        },
    )
    return {"status": "created", "item_id": next_id}


@router.put("/bank/{item_id}", response_model=dict)
def update_content_bank_item(
    item_id: int,
    body: ContentBankItemUpdate,
    sheets: SheetsClientDep,
    _auth: AuthDep,
):
    """Update a content bank item by ID."""
    header, data, _ = sheets.get_tab_data(TAB_CONTENT_BANK, "A:H")
    for row in data:
        row_idx = int(row[0])
        row_dict = dict(zip(header, row[1:]))
        if int(float(row_dict.get("ID", 0) or 0)) == item_id:
            updates = {}
            if body.category is not None:
                updates["Category"] = body.category
            if body.post_type is not None:
                updates["PostType"] = body.post_type
            if body.draft is not None:
                updates["Draft"] = body.draft
            if body.safety_flag is not None:
                updates["SafetyFlag"] = str(body.safety_flag)
            if body.ready is not None:
                updates["Ready"] = "TRUE" if body.ready else "FALSE"
            if body.notes is not None:
                updates["Notes"] = body.notes
            sheets.update_tab_row(TAB_CONTENT_BANK, row_idx, header, updates)
            return {"status": "updated", "item_id": item_id}

    return {"status": "not_found", "item_id": item_id}


@router.delete("/bank/{item_id}", response_model=dict)
def delete_content_bank_item(
    item_id: int,
    sheets: SheetsClientDep,
    _auth: AuthDep,
):
    """Delete a content bank item by ID."""
    header, data, _ = sheets.get_tab_data(TAB_CONTENT_BANK, "A:H")
    for row in data:
        row_idx = int(row[0])
        row_dict = dict(zip(header, row[1:]))
        if int(float(row_dict.get("ID", 0) or 0)) == item_id:
            sheets.delete_tab_row(TAB_CONTENT_BANK, row_idx, len(header))
            return {"status": "deleted", "item_id": item_id}
    return {"status": "not_found", "item_id": item_id}


# ------------------------------------------------------------------
# Repost Bank
# ------------------------------------------------------------------

@router.get("/reposts", response_model=list[RepostBankItemResponse])
def get_repost_bank(sheets: SheetsClientDep, _auth: AuthDep):
    """Get all repost bank items."""
    items = sheets.get_repost_bank()
    return [
        RepostBankItemResponse(
            item_id=i.item_id,
            source_name=i.source_name,
            source_url=i.source_url,
            summary=i.summary,
            commentary_prompt=i.commentary_prompt,
            safety_flag=i.safety_flag,
            last_used=i.last_used,
            notes=i.notes,
        )
        for i in items
    ]


@router.post("/reposts", response_model=dict)
def create_repost_bank_item(
    body: RepostBankItemCreate,
    sheets: SheetsClientDep,
    _auth: AuthDep,
):
    """Add a new repost bank item."""
    existing = sheets.get_repost_bank()
    next_id = max((i.item_id for i in existing), default=0) + 1

    sheets.append_tab_row(
        TAB_REPOST_BANK,
        _REPOST_HEADER,
        {
            "ID": str(next_id),
            "SourceName": body.source_name,
            "SourceURL": body.source_url,
            "Summary": body.summary,
            "CommentaryPrompt": body.commentary_prompt,
            "SafetyFlag": str(body.safety_flag),
            "LastUsed": "",
            "Notes": body.notes or "",
        },
    )
    return {"status": "created", "item_id": next_id}
