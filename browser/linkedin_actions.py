"""
Common LinkedIn DOM interactions via Playwright.

Handles navigation, posting, commenting, liking, and feed scrolling.

SELECTOR STRATEGY (2025+):
LinkedIn uses hashed/obfuscated CSS class names (e.g., "_78a9d91d") that
change frequently. We rely on stable semantic attributes instead:
  - ARIA roles: role="listitem", role="textbox"
  - ARIA labels: aria-label="Reaction button state: ..."
  - Button text content: "Like", "Comment", "Repost", "Send"
  - Data attributes: data-view-name="feed-full-update"
  - Semantic HTML: <time>, <a href="/in/...">

DO NOT use CSS class names as selectors — they will break.
"""

import asyncio
import logging
import random
import re
from typing import Optional

from playwright.async_api import Page, Locator, TimeoutError as PlaywrightTimeout

from browser.human_typing import human_type_into_element
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
# Selectors — use semantic attributes, NOT CSS class names.
# LinkedIn obfuscates class names and changes them without notice.
#
# Last verified: 2026-02-08 via scripts/debug_feed.py
# ---------------------------------------------------------------------------
SEL = {
    # Feed posts (main feed uses listitem, activity pages use data-urn)
    "feed_post": "div[role='listitem']",
    "activity_post": "div[data-urn]",
    "post_update": "[data-view-name='feed-full-update']",
    "post_time": "time",
    "post_author_link": "a[href*='/in/']",

    # Post editor (modal that opens after clicking "Start a post")
    "post_editor": "div[role='textbox']",

    # Comment editor (appears inside a post after clicking Comment)
    "comment_editor": "div[role='textbox']",
}

LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"
LINKEDIN_PROFILE_URL = "https://www.linkedin.com/in/{slug}/recent-activity/all/"

# Button text labels used with Playwright locator text matching.
# These are the visible text on LinkedIn action buttons (not CSS selectors).
BTN_TEXT = {
    "like": "Like",
    "comment": "Comment",
    "repost": "Repost",
    "send": "Send",
}


# ---------------------------------------------------------------------------
# Locator helpers — find buttons by visible text or aria-label
# ---------------------------------------------------------------------------

def _like_button(post: Locator) -> Locator:
    """Locate the Like/reaction button inside a post.

    LinkedIn uses aria-label="Reaction button state: no reaction" for unliked
    and aria-label containing "liked" or "unlike" for already-liked posts.
    """
    return post.locator("button[aria-label*='Reaction button']")


def _comment_button(post: Locator) -> Locator:
    """Locate the Comment button inside a post."""
    return post.locator("button").filter(has_text="Comment").first


def _repost_button(post: Locator) -> Locator:
    """Locate the Repost button inside a post."""
    return post.locator("button").filter(has_text="Repost").first


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Feed post extraction
# ---------------------------------------------------------------------------

async def get_feed_posts(page: Page, max_posts: int = 10) -> list[dict]:
    """Extract visible posts from the feed.

    Returns a list of dicts with keys: text, author, timestamp, element_index.
    Skips promoted posts automatically.
    """
    posts = []
    feed_posts = page.locator(SEL["feed_post"])
    count = await feed_posts.count()

    # Fallback: activity pages use div[data-urn] instead of div[role=listitem]
    if count == 0:
        feed_posts = page.locator(SEL["activity_post"])
        count = await feed_posts.count()

    for idx in range(min(count, max_posts)):
        try:
            post = feed_posts.nth(idx)

            # Get full text of the post
            full_text = await post.inner_text()

            # Skip promoted posts
            if "Promoted" in full_text[:300]:
                continue

            # Extract author from profile links — skip the first one
            # (it wraps the profile image and has empty text)
            author = "Unknown"
            author_links = post.locator(SEL["post_author_link"])
            link_count = await author_links.count()
            for li in range(link_count):
                link_text = (await author_links.nth(li).inner_text()).strip()
                if link_text:
                    author = link_text.split("\n")[0].strip()
                    break

            # Extract timestamp
            timestamp = None
            time_el = post.locator(SEL["post_time"])
            if await time_el.count() > 0:
                timestamp = await time_el.first.get_attribute("datetime")

            # Extract post body text by removing UI chrome lines
            lines = full_text.strip().split("\n")
            noise = {"Like", "Comment", "Repost", "Send", "… more", "…more",
                     "Follow", "Promoted"}
            body_lines = []
            found_timestamp = False
            for l in lines:
                s = l.strip()
                if not s:
                    continue
                # Detect timestamp line ("1d •", "9h •", "2w •", etc.)
                # Once found, everything after is post content
                if not found_timestamp and re.match(
                    r'^(\d+[hdwmo]\s*•|.*ago\s*•)', s
                ):
                    found_timestamp = True
                    continue
                if not found_timestamp:
                    continue
                # Filter UI noise from post content
                if s in noise:
                    continue
                if re.match(r'^Feed post', s):
                    continue
                if re.match(r'^\d+\s*(reactions?|comments?|reposts?|likes?)$', s, re.I):
                    continue
                if re.match(r'^\d[\d,]+$', s):
                    continue
                if s.startswith("Activate to view"):
                    continue
                if "Visible to anyone" in s:
                    continue
                body_lines.append(s)
            # Fallback if timestamp detection missed: skip first 3 header lines
            if not body_lines and lines:
                raw = [l.strip() for l in lines if l.strip()]
                body_lines = raw[3:] if len(raw) > 3 else raw
            body_text = "\n".join(body_lines)

            posts.append({
                "text": body_text[:2000],
                "author": author,
                "timestamp": timestamp,
                "element_index": idx,
            })
        except Exception as e:
            logger.debug("Skipping post %d: %s", idx, e)
            continue

    return posts


# ---------------------------------------------------------------------------
# Post creation
# ---------------------------------------------------------------------------

async def create_post(page: Page, text: str) -> bool:
    """Create a new LinkedIn post.

    Opens the post editor by clicking the "Start a post" trigger at the
    top of the feed, types the content with human-like timing, and submits.

    Uses multiple fallback strategies to find the trigger element since
    LinkedIn changes its DOM structure.

    Returns True on success, False on failure.
    """
    async def _attempt():
        await navigate_to_feed(page)

        # Try multiple strategies to open the post editor
        started = False

        # Strategy 1: Button with "Start a post" text
        if not started:
            btn = page.get_by_role("button", name="Start a post")
            if await btn.count() > 0:
                await btn.first.click()
                started = True

        # Strategy 2: Any clickable element with "Start a post" text
        if not started:
            trigger = page.locator("button, div[role='button'], a, span[role='button']").filter(
                has_text="Start a post"
            )
            if await trigger.count() > 0:
                await trigger.first.click()
                started = True

        # Strategy 3: Placeholder text in a text-like element
        if not started:
            trigger = page.locator(
                "[data-placeholder*='Start a post'], "
                "[aria-placeholder*='Start a post'], "
                "[placeholder*='Start a post']"
            )
            if await trigger.count() > 0:
                await trigger.first.click()
                started = True

        # Strategy 4: "What do you want to talk about" text
        if not started:
            trigger = page.locator("button, div[role='button'], a").filter(
                has_text="What do you want to talk about"
            )
            if await trigger.count() > 0:
                await trigger.first.click()
                started = True

        # Strategy 5: Share box feed entry (data-view-name based)
        if not started:
            trigger = page.locator("[data-view-name*='share-box'], [data-view-name*='new-update']")
            if await trigger.count() > 0:
                await trigger.first.click()
                started = True

        if not started:
            logger.error("Could not find 'Start a post' trigger on the feed page")
            raise Exception("Start a post trigger not found")

        # Wait for the post editor modal
        editor = page.locator(SEL["post_editor"]).first
        await editor.wait_for(timeout=10_000)
        await _random_pause(0.8, 1.5)

        # Type post content with human-like timing
        await human_type_into_element(page, editor, text)
        await _random_pause(1.0, 2.0)

        # Submit — look for a "Post" button (the submit action in the modal)
        submit = page.get_by_role("button", name="Post", exact=True)
        if await submit.count() == 0:
            # Fallback: last button with "Post" text (avoids matching "Repost")
            submit = page.locator("button").filter(has_text="Post").last
        await submit.click()
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


# ---------------------------------------------------------------------------
# Comment on a post
# ---------------------------------------------------------------------------

async def comment_on_post(page: Page, post_index: int, comment_text: str) -> bool:
    """Comment on a post by its index in the current feed view.

    Clicks the Comment button on the specified post, waits for the comment
    editor to appear, types the comment with human-like timing, and submits.

    Returns True on success.
    """
    try:
        feed_posts = page.locator(SEL["feed_post"])
        count = await feed_posts.count()

        # Fallback: activity pages use div[data-urn]
        if count == 0:
            feed_posts = page.locator(SEL["activity_post"])
            count = await feed_posts.count()

        if post_index >= count:
            logger.error("Post index %d out of range (%d posts)", post_index, count)
            return False

        post = feed_posts.nth(post_index)

        # Scroll post into view
        await post.scroll_into_view_if_needed()
        await _random_pause(0.5, 1.0)

        # Click comment button (identified by visible text "Comment")
        comment_btn = _comment_button(post)
        if await comment_btn.count() == 0:
            logger.error("Comment button not found on post %d", post_index)
            return False
        await comment_btn.click()
        await _random_pause(1.0, 2.0)

        # Find the comment editor (textbox within this post's comment section)
        comment_box = post.locator(SEL["comment_editor"]).first
        await comment_box.wait_for(timeout=5_000)

        # Type the comment with human-like timing
        await human_type_into_element(page, comment_box, comment_text)
        await _random_pause(0.8, 1.5)

        # Submit comment
        # LinkedIn's comment submit is typically a button with a paper-plane
        # icon or text like "Post" / "Comment" within the comment area
        submit = post.locator("button").filter(has_text="Post").last
        if await submit.count() > 0:
            await submit.click()
        else:
            # Fallback: look for submit button by aria-label
            submit = post.locator("button[aria-label*='Post'], button[aria-label*='Submit']")
            if await submit.count() > 0:
                await submit.first.click()
            else:
                # Last resort: Ctrl+Enter or Enter to submit
                await page.keyboard.press("Control+Enter")

        await _random_pause(2.0, 4.0)

        logger.info("Commented on post %d (%d chars)", post_index, len(comment_text))
        return True

    except Exception as e:
        logger.error("Failed to comment on post %d: %s", post_index, e)
        return False


# ---------------------------------------------------------------------------
# Like a post
# ---------------------------------------------------------------------------

async def like_post(page: Page, post_index: int) -> bool:
    """Like a post by its index in the current feed view."""
    try:
        feed_posts = page.locator(SEL["feed_post"])
        count = await feed_posts.count()

        # Fallback: activity pages use div[data-urn]
        if count == 0:
            feed_posts = page.locator(SEL["activity_post"])
            count = await feed_posts.count()

        if post_index >= count:
            return False

        post = feed_posts.nth(post_index)
        await post.scroll_into_view_if_needed()
        await _random_pause(0.5, 1.0)

        like_btn = _like_button(post)
        if await like_btn.count() == 0:
            return False

        # Check if already liked via aria-label
        aria = await like_btn.get_attribute("aria-label") or ""
        if "unlike" in aria.lower() or "already" in aria.lower():
            logger.info("Post %d already liked, skipping", post_index)
            return True

        await like_btn.click()
        await _random_pause(1.0, 2.0)
        logger.info("Liked post %d", post_index)
        return True

    except Exception as e:
        logger.error("Failed to like post %d: %s", post_index, e)
        return False


# ---------------------------------------------------------------------------
# Read comments on a post
# ---------------------------------------------------------------------------

async def get_post_comments(page: Page, post_index: int = 0) -> list[dict]:
    """Get comments on a post in the current feed view.

    Clicks the Comment button to expand the comments section (if not already
    visible), then extracts comment author and text.

    Returns list of dicts with keys: author, text.
    """
    comments = []
    try:
        feed_posts = page.locator(SEL["feed_post"])
        post = feed_posts.nth(post_index)

        # Click comment button to expand comments section
        comment_btn = _comment_button(post)
        if await comment_btn.count() > 0:
            await comment_btn.click()
            await _random_pause(1.5, 2.5)

        # Look for comment containers within the post
        # Comments typically have article elements or divs with comment-related
        # data-view-name attributes
        comment_section = post.locator("article")
        count = await comment_section.count()

        if count == 0:
            # Fallback: look for comment-like structures
            comment_section = post.locator("[data-view-name*='comment']")
            count = await comment_section.count()

        for i in range(count):
            try:
                el = comment_section.nth(i)
                full_text = await el.inner_text()

                # Extract author from profile link
                author = "Unknown"
                author_link = el.locator(SEL["post_author_link"]).first
                if await author_link.count() > 0:
                    author = (await author_link.inner_text()).split("\n")[0].strip()

                # Clean up comment text (remove author name from beginning)
                text = full_text.strip()
                if text.startswith(author):
                    text = text[len(author):].strip()

                comments.append({
                    "author": author,
                    "text": text[:500],
                })
            except Exception:
                continue

    except Exception as e:
        logger.debug("Failed to get comments: %s", e)

    return comments


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _random_pause(min_sec: float, max_sec: float) -> None:
    """Sleep for a random duration to simulate human behavior."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))
