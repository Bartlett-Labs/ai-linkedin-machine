#!/usr/bin/env python3
"""
Manual LinkedIn login helper.

Opens a visible browser for a persona and waits for you to log in.
The session cookies are saved to the persona's persistent context
directory and will be reused on all future runs.

Usage:
    python scripts/login.py                    # login as MainUser
    python scripts/login.py "The Deep Learner" # login as a specific persona
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


async def login(persona_name: str = "MainUser"):
    from browser.context_manager import PersonaContext

    print(f"\n=== LinkedIn Login: {persona_name} ===\n")
    print("Opening browser — take your time, it will stay open until you press ENTER.\n")

    ctx = PersonaContext(persona_name, headless=False)
    await ctx.start()

    # Set generous timeouts so slow machines don't kill the browser
    page = await ctx.new_page()
    page.set_default_timeout(120_000)           # 2 minutes for any single action
    page.set_default_navigation_timeout(120_000) # 2 minutes for page loads

    try:
        await page.goto("https://www.linkedin.com/login", wait_until="commit")
    except Exception as e:
        print(f"Navigation hiccup (this is fine): {e}")
        print("The browser is still open — just log in manually.\n")

    print("Browser is open. Log in to LinkedIn at your own pace.")
    print("Once you see the feed, come back here and press ENTER.\n")
    print("  ** The browser will NOT close until you press ENTER **\n")

    # Wait for user to press Enter (run in executor so it doesn't block)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, input, "Press ENTER when logged in > ")

    # Verify we're logged in by checking the URL
    current_url = page.url
    if "feed" in current_url or "mynetwork" in current_url:
        print(f"\nLogin successful! Session saved for '{persona_name}'.")
        print(f"Cookies stored at: ~/.ai-linkedin-machine/sessions/{persona_name.lower().replace(' ', '_')}/")
    else:
        print(f"\nCurrent URL: {current_url}")
        print("Doesn't look like the feed yet, but the session is saved anyway.")
        print("If you completed login, it should work on next run.")

    await ctx.close()
    print("\nDone. You can close this terminal.\n")


if __name__ == "__main__":
    persona = sys.argv[1] if len(sys.argv) > 1 else "MainUser"
    asyncio.run(login(persona))
