"""Shared dependencies for the API layer."""

import hmac
import json
import logging
import os
from functools import lru_cache
from typing import Annotated, Union

from fastapi import Depends, Header, HTTPException, status

logger = logging.getLogger(__name__)

API_KEY = os.getenv("DASHBOARD_API_KEY", "")

# Data backend toggle: "postgres" (default) or "sheets"
_DATA_BACKEND = os.getenv("DATA_BACKEND", "postgres").lower()


def _create_data_client():
    """Create the appropriate data client based on DATA_BACKEND."""
    if _DATA_BACKEND == "postgres":
        from db.client import DatabaseClient
        return DatabaseClient()
    else:
        from sheets.client import SheetsClient
        return SheetsClient()


@lru_cache(maxsize=1)
def get_data_client():
    """Singleton data client shared across all routes."""
    return _create_data_client()


# Backward compatibility alias
get_sheets_client = get_data_client


def verify_api_key(x_api_key: Annotated[str, Header()] = "") -> str:
    """Validate API key from request header.

    If DASHBOARD_API_KEY is not set, auth is disabled (dev mode).
    """
    if not API_KEY:
        return "dev"
    if not hmac.compare_digest(x_api_key, API_KEY):
        logger.warning("Auth failure: invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return x_api_key


DataClientDep = Annotated[object, Depends(get_data_client)]
# Backward compatibility — external consumers may still reference SheetsClientDep
SheetsClientDep = DataClientDep
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
