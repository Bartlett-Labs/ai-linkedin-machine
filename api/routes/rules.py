"""Reply rules and safety terms CRUD routes."""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api.deps import AuthDep, DataClientDep
from db.client import TAB_REPLY_RULES, TAB_SAFETY_TERMS

router = APIRouter(prefix="/rules", tags=["rules"])

_RULES_HEADER = ["ConditionType", "Trigger", "Action", "Notes"]
_SAFETY_HEADER = ["Term", "Response"]


class ReplyRuleResponse(BaseModel):
    condition_type: str
    trigger: str
    action: str
    notes: Optional[str] = None


class ReplyRuleCreate(BaseModel):
    condition_type: str
    trigger: str
    action: str = "IGNORE"
    notes: Optional[str] = None


class SafetyTermResponse(BaseModel):
    term: str
    response: str = "BLOCK"


class SafetyTermCreate(BaseModel):
    term: str
    response: str = "BLOCK"


# ------------------------------------------------------------------
# Reply Rules
# ------------------------------------------------------------------

@router.get("/reply", response_model=list[ReplyRuleResponse])
def get_reply_rules(client: DataClientDep, _auth: AuthDep):
    """Get all reply rules."""
    rules = client.get_reply_rules()
    return [
        ReplyRuleResponse(
            condition_type=r.condition_type,
            trigger=r.trigger,
            action=r.action.value,
            notes=r.notes,
        )
        for r in rules
    ]


@router.post("/reply", response_model=dict)
def create_reply_rule(
    body: ReplyRuleCreate,
    client: DataClientDep,
    _auth: AuthDep,
):
    """Add a new reply rule."""
    client.append_tab_row(
        TAB_REPLY_RULES,
        _RULES_HEADER,
        {
            "ConditionType": body.condition_type,
            "Trigger": body.trigger,
            "Action": body.action,
            "Notes": body.notes or "",
        },
    )
    return {"status": "created", "trigger": body.trigger}


@router.delete("/reply/{trigger}", response_model=dict)
def delete_reply_rule(
    trigger: str,
    client: DataClientDep,
    _auth: AuthDep,
):
    """Delete a reply rule by trigger text."""
    header, data, _ = client.get_tab_data(TAB_REPLY_RULES, "A:D")
    for row in data:
        row_idx = int(row[0])
        row_dict = dict(zip(header, row[1:]))
        if row_dict.get("Trigger", "").strip().lower() == trigger.lower():
            client.delete_tab_row(TAB_REPLY_RULES, row_idx, len(header))
            return {"status": "deleted", "trigger": trigger}
    return {"status": "not_found", "trigger": trigger}


# ------------------------------------------------------------------
# Safety Terms
# ------------------------------------------------------------------

@router.get("/safety", response_model=list[SafetyTermResponse])
def get_safety_terms(client: DataClientDep, _auth: AuthDep):
    """Get all safety terms."""
    terms = client.get_safety_terms()
    return [SafetyTermResponse(term=t.term, response=t.response) for t in terms]


@router.post("/safety", response_model=dict)
def create_safety_term(
    body: SafetyTermCreate,
    client: DataClientDep,
    _auth: AuthDep,
):
    """Add a new safety term."""
    client.append_tab_row(
        TAB_SAFETY_TERMS,
        _SAFETY_HEADER,
        {"Term": body.term, "Response": body.response},
    )
    return {"status": "created", "term": body.term}


@router.delete("/safety/{term}", response_model=dict)
def delete_safety_term(
    term: str,
    client: DataClientDep,
    _auth: AuthDep,
):
    """Delete a safety term."""
    header, data, _ = client.get_tab_data(TAB_SAFETY_TERMS, "A:B")
    for row in data:
        row_idx = int(row[0])
        row_dict = dict(zip(header, row[1:]))
        if row_dict.get("Term", "").strip().lower() == term.lower():
            client.delete_tab_row(TAB_SAFETY_TERMS, row_idx, len(header))
            return {"status": "deleted", "term": term}
    return {"status": "not_found", "term": term}
