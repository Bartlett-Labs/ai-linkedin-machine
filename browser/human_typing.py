"""
Human-like typing simulation for Playwright.

Randomized keystroke delays (50-150ms per char), occasional pauses,
and rare typo+correction sequences to pass automation detection.
"""

import asyncio
import random
import string
from typing import Optional

from playwright.async_api import Page

# Timing constants (milliseconds)
MIN_CHAR_DELAY = 50
MAX_CHAR_DELAY = 150
PAUSE_PROBABILITY = 0.05  # 5% chance of a thinking pause per character
PAUSE_MIN_MS = 300
PAUSE_MAX_MS = 800
TYPO_PROBABILITY = 0.02  # 2% chance of a typo per character

# Characters that are "near" each other on a QWERTY keyboard
NEARBY_KEYS = {
    "a": "sq", "b": "vn", "c": "xv", "d": "sf", "e": "wr",
    "f": "dg", "g": "fh", "h": "gj", "i": "uo", "j": "hk",
    "k": "jl", "l": "k;", "m": "n,", "n": "bm", "o": "ip",
    "p": "o[", "q": "wa", "r": "et", "s": "ad", "t": "ry",
    "u": "yi", "v": "cb", "w": "qe", "x": "zc", "y": "tu",
    "z": "x",
}


def _nearby_typo(char: str) -> str:
    """Return a plausible typo character for the given key."""
    lower = char.lower()
    if lower in NEARBY_KEYS:
        typo = random.choice(NEARBY_KEYS[lower])
        return typo.upper() if char.isupper() else typo
    return random.choice(string.ascii_lowercase)


async def human_type(
    page: Page,
    selector: str,
    text: str,
    *,
    min_delay: int = MIN_CHAR_DELAY,
    max_delay: int = MAX_CHAR_DELAY,
    typo_rate: float = TYPO_PROBABILITY,
) -> None:
    """Type text into an element with human-like timing and occasional typos.

    Args:
        page: Playwright page instance.
        selector: CSS or XPath selector for the target input.
        text: The text to type.
        min_delay: Minimum delay between keystrokes in ms.
        max_delay: Maximum delay between keystrokes in ms.
        typo_rate: Probability of a typo per character (0-1).
    """
    element = page.locator(selector)
    await element.click()
    await asyncio.sleep(random.uniform(0.2, 0.5))

    for char in text:
        # Occasional thinking pause
        if random.random() < PAUSE_PROBABILITY:
            await asyncio.sleep(
                random.randint(PAUSE_MIN_MS, PAUSE_MAX_MS) / 1000
            )

        # Occasional typo + correction
        if random.random() < typo_rate and char.isalpha():
            wrong = _nearby_typo(char)
            await page.keyboard.type(wrong, delay=random.randint(min_delay, max_delay))
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.keyboard.press("Backspace")
            await asyncio.sleep(random.uniform(0.05, 0.15))

        await page.keyboard.type(char, delay=random.randint(min_delay, max_delay))

    # Small pause after finishing typing
    await asyncio.sleep(random.uniform(0.3, 0.7))


async def human_type_into_contenteditable(
    page: Page,
    selector: str,
    text: str,
    *,
    min_delay: int = MIN_CHAR_DELAY,
    max_delay: int = MAX_CHAR_DELAY,
) -> None:
    """Type into a contenteditable div (like LinkedIn's post/comment editors).

    LinkedIn uses contenteditable divs with role='textbox' rather than
    standard input/textarea elements.
    """
    element = page.locator(selector)
    await element.click()
    await asyncio.sleep(random.uniform(0.3, 0.6))

    for char in text:
        if random.random() < PAUSE_PROBABILITY:
            await asyncio.sleep(
                random.randint(PAUSE_MIN_MS, PAUSE_MAX_MS) / 1000
            )

        await page.keyboard.type(char, delay=random.randint(min_delay, max_delay))

    await asyncio.sleep(random.uniform(0.3, 0.7))
