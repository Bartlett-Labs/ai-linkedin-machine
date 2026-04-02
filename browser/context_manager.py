"""
Persistent Playwright browser context manager.

Each persona gets its own user data directory so cookies/sessions persist
between runs. No re-login needed after the first manual authentication.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Playwright,
    Page,
)

logger = logging.getLogger(__name__)

DEFAULT_SESSION_DIR = os.path.expanduser("~/.ai-linkedin-machine/sessions")
VIEWPORT = {"width": 1280, "height": 800}
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class PersonaContext:
    """Manages a persistent Playwright browser context for a single persona."""

    def __init__(
        self,
        persona_name: str,
        session_dir: Optional[str] = None,
        headless: bool = True,
    ):
        self.persona_name = persona_name
        self.session_dir = session_dir or DEFAULT_SESSION_DIR
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    @property
    def user_data_dir(self) -> str:
        safe_name = self.persona_name.lower().replace(" ", "_")
        return os.path.join(self.session_dir, safe_name)

    async def start(self) -> BrowserContext:
        """Launch browser and return a persistent context for this persona."""
        Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)

        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            viewport=VIEWPORT,
            user_agent=USER_AGENT,
            locale="en-US",
            timezone_id="America/Chicago",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
            ignore_default_args=["--enable-automation"],
        )

        # Inject stealth settings to evade automation detection
        await self._apply_stealth(self._context)
        logger.info("Started persistent context for persona: %s", self.persona_name)
        return self._context

    async def _apply_stealth(self, context: BrowserContext) -> None:
        """Apply stealth JS to every page created in this context."""
        await context.add_init_script("""
            // Remove webdriver flag
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

            // Realistic plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });

            // Realistic languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });

            // Chrome runtime
            window.chrome = { runtime: {} };
        """)

    async def new_page(self) -> Page:
        """Create a new page in this persona's context."""
        if self._context is None:
            await self.start()
        page = await self._context.new_page()
        return page

    async def close(self) -> None:
        """Close the browser context (session data persists on disk)."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Closed context for persona: %s", self.persona_name)

    async def __aenter__(self) -> "PersonaContext":
        await self.start()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()


class ContextPool:
    """Manages browser contexts for multiple personas."""

    def __init__(
        self,
        session_dir: Optional[str] = None,
        headless: bool = True,
    ):
        self.session_dir = session_dir or DEFAULT_SESSION_DIR
        self.headless = headless
        self._contexts: dict[str, PersonaContext] = {}

    async def get(self, persona_name: str) -> PersonaContext:
        """Get or create a context for the given persona."""
        if persona_name not in self._contexts:
            ctx = PersonaContext(
                persona_name=persona_name,
                session_dir=self.session_dir,
                headless=self.headless,
            )
            await ctx.start()
            self._contexts[persona_name] = ctx
        return self._contexts[persona_name]

    async def close_all(self) -> None:
        """Close all open persona contexts."""
        for ctx in self._contexts.values():
            await ctx.close()
        self._contexts.clear()

    async def __aenter__(self) -> "ContextPool":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close_all()
