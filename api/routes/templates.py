"""Comment templates CRUD routes."""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api.deps import AuthDep, DataClientDep
from db.client import TAB_COMMENT_TEMPLATES

router = APIRouter(prefix="/templates", tags=["templates"])

_TEMPLATES_HEADER = ["ID", "TemplateText", "Tone", "Category", "SafetyFlag", "ExampleUse", "Persona"]


class CommentTemplateResponse(BaseModel):
    template_id: str
    template_text: str
    tone: str = ""
    category: str = ""
    safety_flag: int = 0
    example_use: str = ""
    persona: str = "MainUser"
    use_count: int = 0


class CommentTemplateCreate(BaseModel):
    template_text: str
    tone: str = ""
    category: str = ""
    safety_flag: int = 0
    example_use: str = ""
    persona: str = "MainUser"


class CommentTemplateUpdate(BaseModel):
    template_text: Optional[str] = None
    tone: Optional[str] = None
    category: Optional[str] = None
    safety_flag: Optional[int] = None
    example_use: Optional[str] = None
    persona: Optional[str] = None


@router.get("", response_model=list[CommentTemplateResponse])
def get_comment_templates(
    client: DataClientDep,
    _auth: AuthDep,
    persona: str = "all",
):
    """Get all comment templates, optionally filtered by persona."""
    templates = client.get_comment_templates(persona=persona)
    return [
        CommentTemplateResponse(
            template_id=t.template_id,
            template_text=t.template_text,
            tone=t.tone,
            category=t.category,
            safety_flag=t.safety_flag,
            example_use=t.example_use,
            persona=t.persona,
            use_count=t.use_count,
        )
        for t in templates
    ]


@router.post("", response_model=dict)
def create_comment_template(
    body: CommentTemplateCreate,
    client: DataClientDep,
    _auth: AuthDep,
):
    """Add a new comment template."""
    existing = client.get_comment_templates(persona="all")
    next_id = max((int(t.template_id) for t in existing if t.template_id.isdigit()), default=0) + 1

    client.append_tab_row(
        TAB_COMMENT_TEMPLATES,
        _TEMPLATES_HEADER,
        {
            "ID": str(next_id),
            "TemplateText": body.template_text,
            "Tone": body.tone,
            "Category": body.category,
            "SafetyFlag": str(body.safety_flag),
            "ExampleUse": body.example_use,
            "Persona": body.persona,
        },
    )
    return {"status": "created", "template_id": next_id}


@router.put("/{template_id}", response_model=dict)
def update_comment_template(
    template_id: str,
    body: CommentTemplateUpdate,
    client: DataClientDep,
    _auth: AuthDep,
):
    """Update a comment template by ID."""
    header, data, _ = client.get_tab_data(TAB_COMMENT_TEMPLATES, "A:G")
    for row in data:
        row_idx = int(row[0])
        row_dict = dict(zip(header, row[1:]))
        if row_dict.get("ID", "").strip() == template_id:
            updates = {}
            if body.template_text is not None:
                updates["TemplateText"] = body.template_text
            if body.tone is not None:
                updates["Tone"] = body.tone
            if body.category is not None:
                updates["Category"] = body.category
            if body.safety_flag is not None:
                updates["SafetyFlag"] = str(body.safety_flag)
            if body.example_use is not None:
                updates["ExampleUse"] = body.example_use
            if body.persona is not None:
                updates["Persona"] = body.persona
            client.update_tab_row(TAB_COMMENT_TEMPLATES, row_idx, header, updates)
            return {"status": "updated", "template_id": template_id}

    return {"status": "not_found", "template_id": template_id}


@router.delete("/{template_id}", response_model=dict)
def delete_comment_template(
    template_id: str,
    client: DataClientDep,
    _auth: AuthDep,
):
    """Delete a comment template by ID."""
    header, data, _ = client.get_tab_data(TAB_COMMENT_TEMPLATES, "A:G")
    for row in data:
        row_idx = int(row[0])
        row_dict = dict(zip(header, row[1:]))
        if row_dict.get("ID", "").strip() == template_id:
            client.delete_tab_row(TAB_COMMENT_TEMPLATES, row_idx, len(header))
            return {"status": "deleted", "template_id": template_id}
    return {"status": "not_found", "template_id": template_id}
