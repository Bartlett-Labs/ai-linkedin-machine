"""Shared dependencies for the API layer."""

import json
import os
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from sheets.client import SheetsClient

API_KEY = os.getenv("DASHBOARD_API_KEY", "")


@lru_cache(maxsize=1)
def get_sheets_client() -> SheetsClient:
    """Singleton SheetsClient shared across all routes."""
    return SheetsClient()


def verify_api_key(x_api_key: Annotated[str, Header()] = "") -> str:
    """Validate API key from request header.

    If DASHBOARD_API_KEY is not set, auth is disabled (dev mode).
    """
    if not API_KEY:
        return "dev"
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return x_api_key


SheetsClientDep = Annotated[SheetsClient, Depends(get_sheets_client)]
AuthDep = Annotated[str, Depends(verify_api_key)]


def load_personas_config() -> list[dict]:
    """Load personas from config/personas.json."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config", "personas.json"
    )
    with open(config_path, "r") as f:
        data = json.load(f)
    return data.get("personas", [])


def save_personas_config(personas: list[dict]) -> None:
    """Save personas to config/personas.json."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config", "personas.json"
    )
    with open(config_path, "w") as f:
        json.dump({"personas": personas}, f, indent=2)
