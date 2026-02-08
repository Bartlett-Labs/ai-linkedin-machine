"""
Common LinkedIn DOM interactions via Playwright.

Handles navigation, posting, commenting, liking, and feed scrolling.
Selectors are centralized here so DOM changes only need one update.
"""

import asyncio
import logging
import random
from typing import Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from browser.human_typing import human_type_into_contenteditable
from utils.retry import retry_async

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Challenge / CAPTCHA detection
# ---------------------------------------------------------------------------

class LinkedInChallengeDetected(Exception):
    """Raised when LinkedIn shows a verification challenge."""
    pass


async def check_for_challenge(page: Page) -> bool:
    """Check if the current page is a LinkedIn challenge screen.

    Detects CAPTCHAs, identity verification, and "unusual activity" warnings.
    Returns True if a challenge is detected.
    """
    challenge_indicators = [
        "checkpoint/challenge",
        "checkpoint/lg",
        "security/verify",
        "/authwall",
    ]

    current_url = page.url
    for indicator in challenge_indicators:
        if indicator in current_url:
            logger.error("LinkedIn challenge detected in URL: %s", current_url)
            return True

    # Check page content for challenge text
    try:
        body_text = await page.inner_text("body")
        challenge_phrases = [
            "Let's do a quick security check",
            "verify your identity",
            "unusual activity",
            "verify that you're a real person",
            "security verification",
        ]
        body_lower = body_text.lower()
        for phrase in challenge_phrases:
            if phrase.lower() in body_lower:
                logger.error("LinkedIn challenge detected: '%s'", phrase)
                return True
    except Exception:
        pass

    return False

# ---------------------------------------------------------------------------
# Selectors (centralized for easy updates when LinkedIn changes DOM)
# ---------------------------------------------------------------------------
SEL = {
    # Feed
    "feed_post": "div.feed-shared-update-v2",
    "post_text": "div.feed-shared-text",
    "post_author": "span.feed-shared-actor__name",
    "post_time": "time",
    "post_urn": "data-urn",
    # Start post dialog
    "start_post_button": "button.share-box-feed-entry__trigger",
    "post_editor": "div.ql-editor[role='textbox']",
    "post_submit": "button.share-actions__primary-action",
    # Comment
    "comment_button": "button[aria-label*='Comment']",
    "comment_editor": "div.ql-editor[role='textbox']",
    "comment_submit": "button[aria-label*='Post comment'], button.comments-comment-box__submit-button",
    # Like
    "like_button": "button[aria-label*='Like']",
    # Reactions on own posts
    "comment_items": "article.comments-comment-item",
    "comment_author": "span.comments-post-meta__name-text",
    "comment_text": "span.comments-comment-item__main-content",
}

LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"
LINKEDIN_PROFILE_URL = "https://www.linkedin.com/in/{slug}/recent-activity/all/"


async def navigate_to_feed(page: Page) -> None:
    """Navigate to the LinkedIn home feed."""
    await page.goto(LINKEDIN_FEED_URL, wait_until="domcontentloaded")
    if await check_for_challenge(page):
        raise LinkedInChallengeDetected(
            f"Challenge on feed navigation for {page.url}. "
            "Pause this persona and resolve manually."
        )
    await page.wait_for_selector(SEL["feed_post"], timeout=15_000)
    await _random_pause(1.5, 3.0)


async def navigate_to_profile_posts(page: Page, profile_slug: str) -> None:
    """Navigate to a user's recent activity page."""
    url = LINKEDIN_PROFILE_URL.format(slug=profile_slug)
    await page.goto(url, wait_until="domcontentloaded")
    if await check_for_challenge(page):
        raise LinkedInChallengeDetected(
            f"Challenge on profile navigation: {profile_slug}. "
            "Pause this persona and resolve manually."
        )
    await _random_pause(2.0, 4.0)


async def scroll_feed(page: Page, scrolls: int = 3) -> None:
    """Scroll the feed to load more posts."""
    for _ in range(scrolls):
        await page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
        await _random_pause(1.5, 3.0)


async def get_feed_posts(page: Page, max_posts: int = 10) -> list[dict]:
    """Extract visible posts from the feed.

    Returns a list of dicts with keys: urn, text, author, timestamp, element_index.
    """
    posts = []
    elements = await page.query_selector_all(SEL["feed_post"])

    for idx, el in enumerate(elements[:max_posts]):
        try:
            text_el = await el.query_selector(SEL["post_text"])
            text = await text_el.inner_text() if text_el else ""

            author_el = await el.query_selector(SEL["post_author"])
            author = await author_el.inner_text() if author_el else "Unknown"

            time_el = await el.query_selector(SEL["post_time"])
            timestamp = await time_el.get_attribute("datetime") if time_el else None

            urn = await el.get_attribute(SEL["post_urn"]) or ""

            posts.append({
                "urn": urn,
                "text": text.strip(),
                "author": author.strip(),
                "timestamp": timestamp,
                "element_index": idx,
            })
        except Exception as e:
            logger.debug("Skipping post %d: %s", idx, e)
            continue

    return posts


async def create_post(page: Page, text: str) -> bool:
    """Create a new LinkedIn post using the feed editor.

    Returns True on success, False on failure. Retries up to 2 times
    on transient failures (not on challenges).
    """
    async def _attempt():
        await navigate_to_feed(page)

        # Click "Start a post"
        await page.click(SEL["start_post_button"])
        await page.wait_for_selector(SEL["post_editor"], timeout=10_000)
        await _random_pause(0.8, 1.5)

        # Type post content
        await human_type_into_contenteditable(page, SEL["post_editor"], text)
        await _random_pause(1.0, 2.0)

        # Submit
        await page.click(SEL["post_submit"])
        await _random_pause(3.0, 5.0)

        logger.info("Post created successfully (%d chars)", len(text))
        return True

    try:
        return await retry_async(_attempt, max_retries=2, base_delay=5.0)
    except LinkedInChallengeDetected:
        logger.error("Challenge detected during post creation - stopping")
        return False
    except Exception as e:
        logger.error("Failed to create post after retries: %s", e)
        return False


async def comment_on_post(page: Page, post_index: int, comment_text: str) -> bool:
    """Comment on a post by its index in the current feed view.

    Returns True on success.
    """
    try:
        posts = await page.query_selector_all(SEL["feed_post"])
        if post_index >= len(posts):
            logger.error("Post index %d out of range (%d posts)", post_index, len(posts))
            return False

        post_el = posts[post_index]

        # Scroll post into view
        await post_el.scroll_into_view_if_needed()
        await _random_pause(0.5, 1.0)

        # Click comment button
        comment_btn = await post_el.query_selector(SEL["comment_button"])
        if not comment_btn:
            logger.error("Comment button not found on post %d", post_index)
            return False
        await comment_btn.click()
        await _random_pause(1.0, 2.0)

        # Find the comment editor within this post's context
        comment_box = await post_el.query_selector(SEL["comment_editor"])
        if not comment_box:
            logger.error("Comment editor not found on post %d", post_index)
            return False

        await comment_box.click()
        await _random_pause(0.3, 0.6)

        # Type the comment with human-like timing
        await human_type_into_contenteditable(
            page,
            f"{SEL['feed_post']}:nth-of-type({post_index + 1}) {SEL['comment_editor']}",
            comment_text,
        )
        await _random_pause(0.8, 1.5)

        # Submit comment
        submit_btn = await post_el.query_selector(SEL["comment_submit"])
        if not submit_btn:
            logger.error("Comment submit button not found on post %d", post_index)
            return False
        await submit_btn.click()
        await _random_pause(2.0, 4.0)

        logger.info("Commented on post %d (%d chars)", post_index, len(comment_text))
        return True

    except Exception as e:
        logger.error("Failed to comment on post %d: %s", post_index, e)
        return False


async def like_post(page: Page, post_index: int) -> bool:
    """Like a post by its index in the current feed view."""
    try:
        posts = await page.query_selector_all(SEL["feed_post"])
        if post_index >= len(posts):
            return False

        post_el = posts[post_index]
        await post_el.scroll_into_view_if_needed()
        await _random_pause(0.5, 1.0)

        like_btn = await post_el.query_selector(SEL["like_button"])
        if not like_btn:
            return False

        # Check if already liked
        aria = await like_btn.get_attribute("aria-pressed")
        if aria == "true":
            logger.info("Post %d already liked, skipping", post_index)
            return True

        await like_btn.click()
        await _random_pause(1.0, 2.0)
        logger.info("Liked post %d", post_index)
        return True

    except Exception as e:
        logger.error("Failed to like post %d: %s", post_index, e)
        return False


async def get_post_comments(page: Page) -> list[dict]:
    """Get comments on the currently visible post.

    Assumes the page is already on a post detail or comment section is expanded.
    Returns list of dicts with keys: author, text.
    """
    comments = []
    elements = await page.query_selector_all(SEL["comment_items"])

    for el in elements:
        try:
            author_el = await el.query_selector(SEL["comment_author"])
            text_el = await el.query_selector(SEL["comment_text"])
            comments.append({
                "author": await author_el.inner_text() if author_el else "Unknown",
                "text": await text_el.inner_text() if text_el else "",
            })
        except Exception:
            continue

    return comments


async def _random_pause(min_sec: float, max_sec: float) -> None:
    """Sleep for a random duration to simulate human behavior."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))
