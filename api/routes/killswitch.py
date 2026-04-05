"""Kill switch API routes — emergency halt for all automation."""

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from api.deps import AuthDep

router = APIRouter(prefix="/kill-switch", tags=["kill-switch"])
logger = logging.getLogger(__name__)


class KillSwitchStatus(BaseModel):
    active: bool
    message: str


@router.get("", response_model=KillSwitchStatus)
def get_kill_switch_status(_auth: AuthDep):
    """Check if the kill switch is active."""
    from utils.kill_switch import check_kill_switch
    active = check_kill_switch()
    return KillSwitchStatus(
        active=active,
        message="Kill switch is ACTIVE — all automation halted" if active else "Kill switch is inactive",
    )


@router.post("/activate", response_model=KillSwitchStatus)
def activate_kill_switch(_auth: AuthDep):
    """Activate the kill switch — halts all automation immediately."""
    from utils.kill_switch import activate_kill_switch
    activate_kill_switch()
    logger.warning("Kill switch ACTIVATED via API")
    return KillSwitchStatus(active=True, message="Kill switch activated — all automation halted")


@router.post("/deactivate", response_model=KillSwitchStatus)
def deactivate_kill_switch(_auth: AuthDep):
    """Deactivate the kill switch — resumes automation."""
    from utils.kill_switch import deactivate_kill_switch
    deactivate_kill_switch()
    logger.info("Kill switch deactivated via API")
    return KillSwitchStatus(active=False, message="Kill switch deactivated — automation resumed")
