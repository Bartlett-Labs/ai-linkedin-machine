"""
Local kill switch that doesn't depend on Google Sheets.

If a file called STOP exists in the project root, all operations halt.
This gives you an emergency stop that works even when the Sheet is
unreachable or API auth has expired.

Usage:
    touch STOP     # halt everything
    rm STOP        # resume operations
"""

import logging
import os

from utils import project_path

logger = logging.getLogger(__name__)

STOP_FILE = project_path("STOP")


def check_kill_switch() -> bool:
    """Returns True if the kill switch is active (STOP file exists)."""
    if os.path.exists(STOP_FILE):
        logger.warning("KILL SWITCH ACTIVE - STOP file found at %s", STOP_FILE)
        return True
    return False


def activate_kill_switch(reason: str = "") -> None:
    """Create the STOP file to halt all operations."""
    with open(STOP_FILE, "w") as f:
        f.write(reason or "Activated programmatically")
    logger.warning("Kill switch ACTIVATED: %s", reason)


def deactivate_kill_switch() -> None:
    """Remove the STOP file to resume operations."""
    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)
        logger.info("Kill switch deactivated")
