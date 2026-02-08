"""
Scheduler - thin wrapper around the orchestrator.

Runs the orchestration cycle on a schedule, respecting posting windows
and phase-based timing from the Google Sheet.
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from scheduling.orchestrator import run_orchestrator
from scheduling.content_calendar import is_in_posting_window, get_next_posting_time
from sheets.client import SheetsClient

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
        sheets_client = SheetsClient()
        logger.info("Connected to Google Sheet")
    except Exception as e:
        logger.warning("Could not connect to Sheet (will retry): %s", e)

    while True:
        try:
            now = datetime.now(TIMEZONE)
            in_window, window_name = is_in_posting_window()

            if in_window:
                logger.info("In posting window: %s", window_name)

                # Reconnect to Sheet if needed
                if sheets_client is None:
                    try:
                        sheets_client = SheetsClient()
                    except Exception as e:
                        logger.error("Still can't connect to Sheet: %s", e)
                        time.sleep(CHECK_INTERVAL_SEC)
                        continue

                # Run orchestrator
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
                next_time = get_next_posting_time()
                if next_time:
                    logger.info(
                        "Outside posting window. Next window at %s",
                        next_time.strftime("%H:%M %Z"),
                    )
                time.sleep(CHECK_INTERVAL_SEC)

        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            break
        except Exception as e:
            logger.error("Scheduler error: %s", e, exc_info=True)
            time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    main()
