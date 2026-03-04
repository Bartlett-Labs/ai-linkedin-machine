"""Engine control routes — mode, phase, feature toggles, kill switch."""

from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api.deps import AuthDep, SheetsClientDep

router = APIRouter(prefix="/engine", tags=["engine"])


class EngineControlResponse(BaseModel):
    mode: str
    phase: str
    main_user_posting: bool
    phantom_engagement: bool
    commenting: bool
    replying: bool
    last_run: Optional[str] = None


class EngineControlUpdate(BaseModel):
    mode: Optional[str] = None
    phase: Optional[str] = None
    main_user_posting: Optional[bool] = None
    phantom_engagement: Optional[bool] = None
    commenting: Optional[bool] = None
    replying: Optional[bool] = None


# Maps our field names to the Sheet's key names
_FIELD_TO_SHEET_KEY = {
    "mode": "Mode",
    "phase": "Phase",
    "main_user_posting": "MainUserPosting",
    "phantom_engagement": "PhantomEngagement",
    "commenting": "Commenting",
    "replying": "Replying",
}


@router.get("", response_model=EngineControlResponse)
def get_engine_control(sheets: SheetsClientDep, _auth: AuthDep):
    """Get current engine control settings."""
    engine = sheets.get_engine_control()
    return EngineControlResponse(
        mode=engine.mode.value,
        phase=engine.phase.value,
        main_user_posting=engine.main_user_posting,
        phantom_engagement=engine.phantom_engagement,
        commenting=engine.commenting,
        replying=engine.replying,
        last_run=engine.last_run,
    )


@router.put("", response_model=EngineControlResponse)
def update_engine_control(
    body: EngineControlUpdate,
    sheets: SheetsClientDep,
    _auth: AuthDep,
):
    """Update engine control settings."""
    updates = {}
    for field_name, sheet_key in _FIELD_TO_SHEET_KEY.items():
        value = getattr(body, field_name)
        if value is not None:
            if isinstance(value, bool):
                updates[sheet_key] = "TRUE" if value else "FALSE"
            else:
                updates[sheet_key] = str(value)

    if updates:
        sheets.update_engine_control(updates)

    return get_engine_control(sheets, _auth)
