"""Configuration loaders for personas and application settings."""

import json

from utils import project_path

PERSONAS_CONFIG = project_path("config", "personas.json")


def load_personas() -> list[dict]:
    """Load all persona definitions from config/personas.json."""
    with open(PERSONAS_CONFIG, "r") as f:
        return json.load(f)["personas"]


def get_persona(name: str) -> dict:
    """Get a single persona by name. Falls back to first persona if not found."""
    personas = load_personas()
    return next((p for p in personas if p["name"] == name), personas[0])
