"""
Scheduler - thin wrapper around the orchestrator.

Runs the orchestration cycle on a schedule, respecting posting windows
and phase-based timing from the Google Sheet.
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Ensure project root is on sys.path and set CWD
_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))
os.chdir(_PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")

from utils import project_path
from scheduling.orchestrator import run_orchestrator
from scheduling.content_calendar import is_in_posting_window, get_next_posting_time
from scheduling.heartbeat import run_all_heartbeats


def _get_data_client():
    """Get the appropriate data client based on DATA_BACKEND env var."""
    backend = os.getenv("DATA_BACKEND", "postgres").lower()
    if backend == "postgres":
        from db.client import DatabaseClient
        return DatabaseClient()
    else:
        from sheets.client import SheetsClient
        return SheetsClient()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TIMEZONE = ZoneInfo("America/Chicago")
CHECK_INTERVAL_SEC = 300  # Check every 5 minutes


def main():
    """Run the scheduler loop."""
    logger.info("Scheduler started")

    headless = os.getenv("HEADLESS", "true").lower() == "true"

    sheets_client = None
    try:
        sheets_client = _get_data_client()
        logger.info("Connected to data backend")
    except Exception as e:
        logger.warning("Could not connect to data backend (will retry): %s", e)

    # Load activity windows from Sheet (if tab exists), otherwise use defaults
    activity_windows = []
    if sheets_client:
        try:
            activity_windows = sheets_client.get_activity_windows()
            if activity_windows:
                enabled = [w for w in activity_windows if w.enabled]
                logger.info(
                    "Loaded %d activity windows from Sheet (%d enabled)",
                    len(activity_windows), len(enabled),
                )
        except Exception as e:
            logger.debug("Could not load ActivityWindows from Sheet: %s", e)

    # Track last heartbeat run time to respect cycle intervals
    last_heartbeat_time = 0.0

    while True:
        try:
            now = datetime.now(TIMEZONE)
            in_window, window_name = is_in_posting_window(activity_windows)

            if in_window:
                logger.info("In posting window: %s", window_name)

                # Reconnect to data backend if needed
                if sheets_client is None:
                    try:
                        sheets_client = _get_data_client()
                    except Exception as e:
                        logger.error("Still can't connect to data backend: %s", e)
                        time.sleep(CHECK_INTERVAL_SEC)
                        continue

                # Reload activity windows from Sheet each cycle
                try:
                    fresh_windows = sheets_client.get_activity_windows()
                    if fresh_windows:
                        activity_windows = fresh_windows
                except Exception:
                    pass

                # Run orchestrator (MainUser pipeline)
                summary = asyncio.run(
                    run_orchestrator(
                        sheets_client=sheets_client,
                        headless=headless,
                    )
                )
                logger.info("Cycle summary: %s", summary)

                # After a successful cycle, wait longer to avoid
                # running again in the same window
                time.sleep(CHECK_INTERVAL_SEC * 6)  # ~30 minutes
            else:
                next_time = get_next_posting_time(activity_windows=activity_windows)
                if next_time:
                    logger.info(
                        "Outside posting window. Next window at %s",
                        next_time.strftime("%H:%M %Z"),
                    )
                time.sleep(CHECK_INTERVAL_SEC)

            # --- Phantom persona heartbeats (independent of posting window) ---
            # Run every CHECK_INTERVAL; each persona's active_hours are checked internally
            elapsed_since_heartbeat = time.time() - last_heartbeat_time
            if elapsed_since_heartbeat >= CHECK_INTERVAL_SEC:
                try:
                    heartbeat_results = asyncio.run(
                        run_all_heartbeats(dry_run=False, headless=headless)
                    )
                    if heartbeat_results:
                        total = sum(
                            len(r.get("comments", [])) + len(r.get("kyle_comments", []))
                            for r in heartbeat_results
                        )
                        logger.info("Heartbeat cycle: %d persona(s), %d total comments",
                                    len(heartbeat_results), total)
                    last_heartbeat_time = time.time()
                except Exception as e:
                    logger.error("Heartbeat error: %s", e, exc_info=True)
                    last_heartbeat_time = time.time()  # Don't retry immediately

        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            break
        except Exception as e:
            logger.error("Scheduler error: %s", e, exc_info=True)
            time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    main()
