"""Persona configuration routes."""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api.deps import AuthDep, load_personas_config, save_personas_config

router = APIRouter(prefix="/personas", tags=["personas"])


class PersonaSummary(BaseModel):
    name: str
    display_name: str
    persona: str
    location: Optional[str] = None
    active_hours: Optional[dict] = None
    behavior: Optional[dict] = None


class PersonaDetail(BaseModel):
    name: str
    display_name: str
    persona: str
    system_prompt: str = ""
    session_dir: str = ""
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    active_hours: Optional[dict] = None
    voice: Optional[dict] = None
    engagement_rules: Optional[dict] = None
    behavior: Optional[dict] = None


class PersonaUpdate(BaseModel):
    display_name: Optional[str] = None
    persona: Optional[str] = None
    system_prompt: Optional[str] = None
    location: Optional[str] = None
    active_hours: Optional[dict] = None
    voice: Optional[dict] = None
    engagement_rules: Optional[dict] = None
    behavior: Optional[dict] = None


@router.get("", response_model=list[PersonaSummary])
def get_personas(_auth: AuthDep):
    """Get all personas (summary view)."""
    personas = load_personas_config()
    return [
        PersonaSummary(
            name=p["name"],
            display_name=p.get("display_name", p["name"]),
            persona=p.get("persona", ""),
            location=p.get("location"),
            active_hours=p.get("active_hours"),
            behavior=p.get("behavior"),
        )
        for p in personas
    ]


@router.get("/{persona_name}", response_model=PersonaDetail)
def get_persona(persona_name: str, _auth: AuthDep):
    """Get a single persona with full details."""
    personas = load_personas_config()
    for p in personas:
        if p["name"].lower() == persona_name.lower():
            return PersonaDetail(
                name=p["name"],
                display_name=p.get("display_name", p["name"]),
                persona=p.get("persona", ""),
                system_prompt=p.get("system_prompt", ""),
                session_dir=p.get("session_dir", ""),
                location=p.get("location"),
                linkedin_url=p.get("linkedin_url"),
                active_hours=p.get("active_hours"),
                voice=p.get("voice"),
                engagement_rules=p.get("engagement_rules"),
                behavior=p.get("behavior"),
            )
    return PersonaDetail(name="not_found", display_name="Not Found", persona="")


@router.put("/{persona_name}", response_model=dict)
def update_persona(
    persona_name: str,
    body: PersonaUpdate,
    _auth: AuthDep,
):
    """Update a persona's configuration."""
    personas = load_personas_config()
    for p in personas:
        if p["name"].lower() == persona_name.lower():
            if body.display_name is not None:
                p["display_name"] = body.display_name
            if body.persona is not None:
                p["persona"] = body.persona
            if body.system_prompt is not None:
                p["system_prompt"] = body.system_prompt
            if body.location is not None:
                p["location"] = body.location
            if body.active_hours is not None:
                p["active_hours"] = body.active_hours
            if body.voice is not None:
                p["voice"] = body.voice
            if body.engagement_rules is not None:
                p["engagement_rules"] = body.engagement_rules
            if body.behavior is not None:
                p["behavior"] = body.behavior
            save_personas_config(personas)
            return {"status": "updated", "name": persona_name}

    return {"status": "not_found", "name": persona_name}
