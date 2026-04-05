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
LINKEDIN_PROFILE_BASE = "https://www.linkedin.com/in/{slug}/"
LINKEDIN_SEARCH_PEOPLE_URL = "https://www.linkedin.com/search/results/people/?keywords={query}&origin=GLOBAL_SEARCH_HEADER"
LINKEDIN_MY_NETWORK_URL = "https://www.linkedin.com/mynetwork/"
LINKEDIN_MESSAGING_URL = "https://www.linkedin.com/messaging/thread/new/"
LINKEDIN_MESSAGING_INBOX_URL = "https://www.linkedin.com/messaging/"

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
        count = await feed_posts.count()
        # Fallback: activity pages use div[data-urn] instead of div[role=listitem]
        if count == 0:
            feed_posts = page.locator(SEL["activity_post"])
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
                author = ""
                author_link = el.locator(SEL["post_author_link"]).first
                if await author_link.count() > 0:
                    author = (await author_link.inner_text()).split("\n")[0].strip()

                # Fallback: use the first non-empty line as author name
                if not author:
                    lines = [l.strip() for l in full_text.split("\n") if l.strip()]
                    if lines:
                        # First line is often the author name
                        candidate = lines[0]
                        # Sanity check: author names are short (< 50 chars)
                        # and don't look like post content
                        if len(candidate) < 50 and not any(
                            c in candidate for c in [".", "!", "?", ","]
                        ):
                            author = candidate
                if not author:
                    author = "Unknown"

                # Clean up comment text (remove author name from beginning)
                text = full_text.strip()
                if author != "Unknown" and text.startswith(author):
                    text = text[len(author):].strip()
                # Strip LinkedIn connection/degree indicators (e.g. "• 1st", "• 2nd")
                text = re.sub(r'^[•·]\s*\d+(st|nd|rd|th)\s*', '', text).strip()

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
# Profile scraping
# ---------------------------------------------------------------------------

async def get_profile_info(page: Page, profile_url: str) -> Optional[dict]:
    """Navigate to a profile and extract key information.

    Returns dict with: name, headline, about, location, experience (list),
    mutual_connections, profile_url. Returns None on failure.
    """
    try:
        # Normalize URL — ensure it points to the main profile page
        url = profile_url.rstrip("/")
        if "/recent-activity" in url:
            url = url.split("/recent-activity")[0]
        if not url.endswith("/"):
            url += "/"

        await page.goto(url, wait_until="domcontentloaded")
        if await check_for_challenge(page):
            raise LinkedInChallengeDetected("Challenge on profile visit")
        await _random_pause(2.0, 4.0)

        info: dict = {"profile_url": url}

        # Name — h1 on the profile page
        name_el = page.locator("h1").first
        if await name_el.count() > 0:
            info["name"] = (await name_el.inner_text()).strip()

        # Headline — usually the text just below the name
        headline_el = page.locator("div.text-body-medium").first
        if await headline_el.count() > 0:
            info["headline"] = (await headline_el.inner_text()).strip()
        else:
            # Fallback: aria-label or meta
            headline_el = page.locator("[data-anonymize='headline']").first
            if await headline_el.count() > 0:
                info["headline"] = (await headline_el.inner_text()).strip()

        # Location
        loc_el = page.locator("span.text-body-small").first
        if await loc_el.count() > 0:
            loc_text = (await loc_el.inner_text()).strip()
            if loc_text and len(loc_text) < 100:
                info["location"] = loc_text

        # Mutual connections count
        try:
            mutual_el = page.locator("span").filter(has_text="mutual connection")
            if await mutual_el.count() > 0:
                mutual_text = (await mutual_el.first.inner_text()).strip()
                match = re.search(r"(\d+)", mutual_text)
                info["mutual_connections"] = int(match.group(1)) if match else 0
        except Exception:
            info["mutual_connections"] = 0

        # About section
        try:
            about_section = page.locator("#about").locator("..").locator("..")
            if await about_section.count() > 0:
                about_text_el = about_section.locator("div.display-flex span[aria-hidden='true']").first
                if await about_text_el.count() > 0:
                    info["about"] = (await about_text_el.inner_text()).strip()[:500]
        except Exception:
            pass

        # Experience — first 3 entries
        try:
            exp_section = page.locator("#experience").locator("..").locator("..")
            if await exp_section.count() > 0:
                exp_items = exp_section.locator("li.artdeco-list__item")
                exp_count = await exp_items.count()
                experiences = []
                for i in range(min(exp_count, 3)):
                    exp_text = (await exp_items.nth(i).inner_text()).strip()
                    # Clean up to just title + company
                    lines = [l.strip() for l in exp_text.split("\n") if l.strip()]
                    if lines:
                        experiences.append(" | ".join(lines[:3]))
                info["experience"] = experiences
        except Exception:
            info["experience"] = []

        logger.info("Scraped profile: %s (%s)", info.get("name", "?"), info.get("headline", "?")[:60])
        return info

    except LinkedInChallengeDetected:
        raise
    except Exception as e:
        logger.error("Failed to scrape profile %s: %s", profile_url, e)
        return None


# ---------------------------------------------------------------------------
# Connection requests
# ---------------------------------------------------------------------------

async def send_connection_request(page: Page, profile_url: str, note: str = "") -> bool:
    """Send a connection request to a person on their profile page.

    Navigates to the profile, clicks Connect, optionally adds a note,
    and sends the request.

    Args:
        page: Playwright page.
        profile_url: LinkedIn profile URL.
        note: Optional personalized note (max 300 chars, truncated if longer).

    Returns True if the request was sent successfully.
    """
    try:
        # Navigate to profile if not already there
        current = page.url
        normalized = profile_url.rstrip("/")
        if normalized not in current:
            url = normalized + "/"
            await page.goto(url, wait_until="domcontentloaded")
            if await check_for_challenge(page):
                raise LinkedInChallengeDetected("Challenge on profile page")
            await _random_pause(2.0, 4.0)

        # Look for Connect button — multiple strategies
        connect_btn = None

        # Strategy 1: Primary Connect button on profile
        btn = page.get_by_role("button", name="Connect")
        if await btn.count() > 0:
            connect_btn = btn.first

        # Strategy 2: "More" dropdown → Connect
        if not connect_btn:
            more_btn = page.get_by_role("button", name="More actions")
            if await more_btn.count() > 0:
                await more_btn.click()
                await _random_pause(0.5, 1.0)
                dropdown_connect = page.locator("div[role='menu']").locator("span").filter(has_text="Connect")
                if await dropdown_connect.count() > 0:
                    connect_btn = dropdown_connect.first

        # Strategy 3: "More" button (icon only)
        if not connect_btn:
            more_btn = page.locator("button[aria-label*='More']").first
            if await more_btn.count() > 0:
                await more_btn.click()
                await _random_pause(0.5, 1.0)
                dropdown_connect = page.locator("div[role='menu']").locator("span").filter(has_text="Connect")
                if await dropdown_connect.count() > 0:
                    connect_btn = dropdown_connect.first

        if not connect_btn:
            logger.warning("Connect button not found on %s (may already be connected)", profile_url)
            return False

        await connect_btn.click()
        await _random_pause(1.0, 2.0)

        # Check if "How do you know" dialog appeared
        how_know = page.locator("button").filter(has_text="Other")
        if await how_know.count() > 0:
            await how_know.click()
            await _random_pause(0.5, 1.0)
            connect_submit = page.locator("button").filter(has_text="Connect")
            if await connect_submit.count() > 0:
                await connect_submit.first.click()
                await _random_pause(1.0, 2.0)

        # Add a note if provided
        if note:
            note = note[:300]  # LinkedIn hard limit

            # Look for "Add a note" button in the connection dialog
            add_note_btn = page.locator("button").filter(has_text="Add a note")
            if await add_note_btn.count() > 0:
                await add_note_btn.click()
                await _random_pause(0.5, 1.0)

                # Find the note textarea
                note_area = page.locator("textarea[name='message'], textarea#custom-message")
                if await note_area.count() == 0:
                    note_area = page.locator("textarea").first

                if await note_area.count() > 0:
                    await note_area.fill("")
                    await human_type_into_element(page, note_area, note)
                    await _random_pause(0.5, 1.0)

        # Click Send / Send invitation
        send_btn = page.locator("button").filter(has_text="Send")
        if await send_btn.count() == 0:
            send_btn = page.locator("button[aria-label*='Send']")
        if await send_btn.count() > 0:
            await send_btn.first.click()
            await _random_pause(2.0, 4.0)
            logger.info("Connection request sent to %s (note: %d chars)", profile_url, len(note))
            return True

        # Fallback: look for "Done" button (some flows)
        done_btn = page.locator("button").filter(has_text="Done")
        if await done_btn.count() > 0:
            await done_btn.click()
            await _random_pause(1.0, 2.0)
            logger.info("Connection request sent (via Done) to %s", profile_url)
            return True

        logger.error("Could not find Send button for connection request")
        return False

    except LinkedInChallengeDetected:
        raise
    except Exception as e:
        logger.error("Failed to send connection request to %s: %s", profile_url, e)
        return False


# ---------------------------------------------------------------------------
# LinkedIn People Search
# ---------------------------------------------------------------------------

async def search_linkedin_people(
    page: Page,
    query: str,
    max_results: int = 10,
) -> list[dict]:
    """Search LinkedIn for people matching a query.

    Returns list of dicts: name, headline, location, profile_url, mutual_connections.
    """
    try:
        from urllib.parse import quote
        url = LINKEDIN_SEARCH_PEOPLE_URL.format(query=quote(query))
        await page.goto(url, wait_until="domcontentloaded")
        if await check_for_challenge(page):
            raise LinkedInChallengeDetected("Challenge on search")
        await _random_pause(3.0, 5.0)

        results = []
        # Search result items are typically in a list
        result_items = page.locator("div.entity-result__item, li.reusable-search__result-container")
        count = await result_items.count()

        if count == 0:
            # Fallback: broader selector
            result_items = page.locator("[data-view-name*='search-entity']")
            count = await result_items.count()

        for i in range(min(count, max_results)):
            try:
                item = result_items.nth(i)
                entry: dict = {}

                # Profile link + name
                profile_link = item.locator("a[href*='/in/']").first
                if await profile_link.count() > 0:
                    href = await profile_link.get_attribute("href")
                    entry["profile_url"] = href.split("?")[0] if href else ""
                    name_text = (await profile_link.inner_text()).strip()
                    # Name is usually the first non-empty line
                    name_lines = [l.strip() for l in name_text.split("\n") if l.strip()]
                    entry["name"] = name_lines[0] if name_lines else "Unknown"

                # Headline
                headline_el = item.locator("div.entity-result__primary-subtitle, div.linked-area div.t-14")
                if await headline_el.count() > 0:
                    entry["headline"] = (await headline_el.first.inner_text()).strip()

                # Location
                loc_el = item.locator("div.entity-result__secondary-subtitle, div.linked-area div.t-12")
                if await loc_el.count() > 0:
                    entry["location"] = (await loc_el.first.inner_text()).strip()

                # Mutual connections
                mutual_el = item.locator("span").filter(has_text="mutual connection")
                if await mutual_el.count() > 0:
                    m_text = (await mutual_el.first.inner_text()).strip()
                    match = re.search(r"(\d+)", m_text)
                    entry["mutual_connections"] = int(match.group(1)) if match else 0
                else:
                    entry["mutual_connections"] = 0

                if entry.get("profile_url"):
                    results.append(entry)

            except Exception as e:
                logger.debug("Skipping search result %d: %s", i, e)
                continue

        logger.info("LinkedIn people search '%s': found %d results", query, len(results))
        return results

    except LinkedInChallengeDetected:
        raise
    except Exception as e:
        logger.error("LinkedIn people search failed for '%s': %s", query, e)
        return []


# ---------------------------------------------------------------------------
# My Network — Accept Pending Invitations
# ---------------------------------------------------------------------------

async def accept_pending_invitations(page: Page, max_accepts: int = 50) -> list[dict]:
    """Accept pending connection invitations on My Network.

    Navigates to the invitation manager and clicks Accept on each pending request.

    Returns list of dicts: name, profile_url, headline for each accepted invitation.
    """
    accepted = []
    try:
        await page.goto(
            "https://www.linkedin.com/mynetwork/invitation-manager/",
            wait_until="domcontentloaded",
        )
        if await check_for_challenge(page):
            raise LinkedInChallengeDetected("Challenge on invitation manager")
        await _random_pause(2.0, 4.0)

        # Each invitation is a card/list item in the invitation manager
        invite_cards = page.locator(
            "li.invitation-card, "
            "li.mn-invitation-list__invitation-card, "
            "div[data-view-name='invitation-card']"
        )
        # Fallback: broader selector for invitation items
        count = await invite_cards.count()
        if count == 0:
            invite_cards = page.locator("section.mn-invitation-manager__invitations li")
            count = await invite_cards.count()
        if count == 0:
            # Try the most generic approach — look for Accept buttons
            accept_buttons = page.locator("button").filter(has_text="Accept")
            count = await accept_buttons.count()
            if count > 0:
                logger.info("Found %d Accept buttons (generic fallback)", count)
                for i in range(min(count, max_accepts)):
                    try:
                        btn = page.locator("button").filter(has_text="Accept").first
                        if await btn.count() == 0:
                            break
                        # Try to extract name from nearby elements
                        parent = btn.locator("xpath=ancestor::li[1]")
                        name = ""
                        profile_url = ""
                        if await parent.count() > 0:
                            link = parent.locator("a[href*='/in/']").first
                            if await link.count() > 0:
                                name = (await link.inner_text()).strip().split("\n")[0]
                                href = await link.get_attribute("href")
                                profile_url = href.split("?")[0] if href else ""

                        await btn.click()
                        await _random_pause(1.0, 3.0)
                        accepted.append({
                            "name": name or f"Connection {i+1}",
                            "profile_url": profile_url,
                        })
                        logger.info("Accepted invitation from %s", name or f"#{i+1}")
                    except Exception as e:
                        logger.warning("Failed to accept invitation %d: %s", i, e)
                        continue
                return accepted

            logger.info("No pending invitations found")
            return []

        logger.info("Found %d pending invitations", count)

        for i in range(min(count, max_accepts)):
            try:
                card = invite_cards.nth(i)
                entry: dict = {}

                # Extract name and profile URL
                link = card.locator("a[href*='/in/']").first
                if await link.count() > 0:
                    href = await link.get_attribute("href")
                    entry["profile_url"] = href.split("?")[0] if href else ""
                    entry["name"] = (await link.inner_text()).strip().split("\n")[0]

                # Extract headline if visible
                subtitle = card.locator("span.invitation-card__subtitle, span.mn-invitation-card__subtitle")
                if await subtitle.count() > 0:
                    entry["headline"] = (await subtitle.first.inner_text()).strip()

                # Click Accept button
                accept_btn = card.locator("button").filter(has_text="Accept")
                if await accept_btn.count() > 0:
                    await accept_btn.first.click()
                    await _random_pause(1.0, 3.0)
                    accepted.append(entry)
                    logger.info("Accepted invitation from %s", entry.get("name", f"#{i+1}"))
                else:
                    logger.debug("No Accept button found on invitation card %d", i)

            except Exception as e:
                logger.warning("Error accepting invitation %d: %s", i, e)
                continue

        logger.info("Accepted %d invitations", len(accepted))
        return accepted

    except LinkedInChallengeDetected:
        raise
    except Exception as e:
        logger.error("Failed to accept invitations: %s", e)
        return accepted


# ---------------------------------------------------------------------------
# My Network — New Connections (acceptances)
# ---------------------------------------------------------------------------

async def get_new_connections(page: Page, max_results: int = 20) -> list[dict]:
    """Check My Network page for recently accepted connections.

    Returns list of dicts: name, profile_url, headline, connected_at.
    """
    try:
        await page.goto(LINKEDIN_MY_NETWORK_URL, wait_until="domcontentloaded")
        if await check_for_challenge(page):
            raise LinkedInChallengeDetected("Challenge on My Network")
        await _random_pause(2.0, 3.0)

        # Look for "Manage" → recent connections section
        # Navigate to connections list
        manage_link = page.locator("a[href*='/mynetwork/invite-connect/connections/']")
        if await manage_link.count() > 0:
            await manage_link.first.click()
            await _random_pause(2.0, 3.0)

        connections = []
        # Connection items
        conn_items = page.locator("li.mn-connection-card, li.reusable-search__result-container")
        count = await conn_items.count()

        for i in range(min(count, max_results)):
            try:
                item = conn_items.nth(i)
                entry: dict = {}

                link = item.locator("a[href*='/in/']").first
                if await link.count() > 0:
                    href = await link.get_attribute("href")
                    entry["profile_url"] = href.split("?")[0] if href else ""
                    entry["name"] = (await link.inner_text()).strip().split("\n")[0]

                time_el = item.locator("time")
                if await time_el.count() > 0:
                    entry["connected_at"] = await time_el.first.get_attribute("datetime")

                if entry.get("profile_url"):
                    connections.append(entry)
            except Exception:
                continue

        logger.info("Found %d connections on My Network", len(connections))
        return connections

    except LinkedInChallengeDetected:
        raise
    except Exception as e:
        logger.error("Failed to get new connections: %s", e)
        return []


# ---------------------------------------------------------------------------
# Direct Messaging — Inbox Reading
# ---------------------------------------------------------------------------

async def get_unread_conversations(
    page: Page,
    max_conversations: int = 15,
) -> list[dict]:
    """Navigate to messaging inbox and find unread conversations.

    Returns list of dicts: sender, profile_url, last_message_preview,
    unread (bool), thread_index (int for clicking back into it).
    """
    conversations = []
    try:
        await page.goto(LINKEDIN_MESSAGING_INBOX_URL, wait_until="domcontentloaded")
        if await check_for_challenge(page):
            raise LinkedInChallengeDetected("Challenge on messaging inbox")
        await _random_pause(2.0, 4.0)

        # Conversation list items in the left panel
        conv_items = page.locator(
            "li.msg-conversation-listitem, "
            "li.msg-conversations-container__convo-item, "
            "div.msg-conversation-card"
        )
        count = await conv_items.count()

        if count == 0:
            # Broader fallback — look for conversation list items
            conv_items = page.locator("ul.msg-conversations-container__conversations-list > li")
            count = await conv_items.count()

        logger.info("Found %d conversations in inbox", count)

        for i in range(min(count, max_conversations)):
            try:
                item = conv_items.nth(i)
                entry: dict = {"thread_index": i}

                # Check if unread — look for unread indicator (bold text, dot, etc.)
                unread_dot = item.locator(
                    "span.msg-conversation-card__unread-count, "
                    "span[data-test-unread-count], "
                    ".notification-badge, "
                    ".msg-conversation-listitem__unread-indicator"
                )
                # Also check if the item has a bold/unread class
                item_classes = await item.get_attribute("class") or ""
                is_unread = (
                    await unread_dot.count() > 0
                    or "unread" in item_classes.lower()
                    or "active" in item_classes.lower()
                )
                entry["unread"] = is_unread

                # Sender name
                name_el = item.locator(
                    "h3.msg-conversation-listitem__participant-names, "
                    "h3.msg-conversation-card__participant-names, "
                    "span.msg-conversation-card__participant-names"
                )
                if await name_el.count() > 0:
                    entry["sender"] = (await name_el.first.inner_text()).strip()
                else:
                    # Fallback: first link text
                    link = item.locator("a").first
                    if await link.count() > 0:
                        entry["sender"] = (await link.inner_text()).strip().split("\n")[0]

                # Last message preview
                preview_el = item.locator(
                    "p.msg-conversation-card__message-snippet, "
                    "p.msg-conversation-listitem__message-snippet, "
                    "span.msg-conversation-card__message-snippet-body"
                )
                if await preview_el.count() > 0:
                    entry["last_message_preview"] = (await preview_el.first.inner_text()).strip()

                # Profile URL from link
                link = item.locator("a[href*='/in/'], a[href*='/messaging/thread/']").first
                if await link.count() > 0:
                    href = await link.get_attribute("href")
                    if href and "/in/" in href:
                        entry["profile_url"] = href.split("?")[0]
                    elif href:
                        entry["thread_url"] = href.split("?")[0]

                if entry.get("sender"):
                    conversations.append(entry)
            except Exception as e:
                logger.debug("Error reading conversation item %d: %s", i, e)
                continue

        return conversations

    except LinkedInChallengeDetected:
        raise
    except Exception as e:
        logger.error("Failed to get conversations: %s", e)
        return []


async def read_conversation_messages(
    page: Page,
    thread_index: int,
    max_messages: int = 10,
) -> list[dict]:
    """Click into a conversation and read recent messages.

    Args:
        page: Playwright page (should already be on messaging inbox).
        thread_index: Index of the conversation in the list to click into.
        max_messages: Max messages to read from the thread.

    Returns list of dicts: author, text, timestamp, is_self.
    """
    messages = []
    try:
        # Click the conversation item to open it
        conv_items = page.locator(
            "li.msg-conversation-listitem, "
            "li.msg-conversations-container__convo-item, "
            "div.msg-conversation-card"
        )
        count = await conv_items.count()
        if count == 0:
            conv_items = page.locator("ul.msg-conversations-container__conversations-list > li")
            count = await conv_items.count()

        if thread_index >= count:
            logger.warning("Thread index %d out of range (%d conversations)", thread_index, count)
            return []

        await conv_items.nth(thread_index).click()
        await _random_pause(1.5, 3.0)

        # Read messages from the conversation panel (right side)
        msg_items = page.locator(
            "li.msg-s-message-list__event, "
            "div.msg-s-event-listitem, "
            "div.msg-s-message-group__message-list li"
        )
        msg_count = await msg_items.count()

        if msg_count == 0:
            # Broader fallback
            msg_items = page.locator("ul.msg-s-message-list-content > li")
            msg_count = await msg_items.count()

        # Read the last N messages (most recent at bottom)
        start = max(0, msg_count - max_messages)

        for i in range(start, msg_count):
            try:
                msg = msg_items.nth(i)
                entry: dict = {}

                # Author name
                sender_el = msg.locator(
                    "span.msg-s-message-group__name, "
                    "span.msg-s-event-listitem__name, "
                    "a.msg-s-message-group__profile-link"
                )
                if await sender_el.count() > 0:
                    entry["author"] = (await sender_el.first.inner_text()).strip()

                # Message text
                text_el = msg.locator(
                    "p.msg-s-event-listitem__body, "
                    "div.msg-s-event-listitem__body, "
                    "p.msg-s-message-body, "
                    "div.msg-s-event__content"
                )
                if await text_el.count() > 0:
                    entry["text"] = (await text_el.first.inner_text()).strip()

                # Timestamp
                time_el = msg.locator("time, span.msg-s-message-group__timestamp")
                if await time_el.count() > 0:
                    dt = await time_el.first.get_attribute("datetime")
                    entry["timestamp"] = dt or (await time_el.first.inner_text()).strip()

                # Detect if this is our own message
                msg_classes = await msg.get_attribute("class") or ""
                entry["is_self"] = "from-me" in msg_classes or "outbound" in msg_classes

                if entry.get("text"):
                    messages.append(entry)
            except Exception as e:
                logger.debug("Error reading message %d: %s", i, e)
                continue

        logger.info("Read %d messages from conversation %d", len(messages), thread_index)
        return messages

    except Exception as e:
        logger.error("Failed to read conversation %d: %s", thread_index, e)
        return []


async def send_dm_reply(page: Page, reply_text: str) -> bool:
    """Type and send a reply in the currently open conversation.

    The conversation must already be open (via read_conversation_messages
    or by clicking a thread). Finds the message compose box, types the
    reply with human-like speed, and clicks Send.

    Returns True if the reply was sent successfully.
    """
    try:
        # Find the message compose textbox
        msg_box = page.locator(
            "div.msg-form__contenteditable[role='textbox'], "
            "div.msg-form__msg-content-container div[role='textbox'], "
            "div[role='textbox']"
        ).last

        if await msg_box.count() == 0:
            logger.error("No message compose box found in conversation")
            return False

        await msg_box.click()
        await _random_pause(0.3, 0.8)

        # Type with human-like delays
        await human_type_into_element(page, msg_box, reply_text)
        await _random_pause(0.5, 1.5)

        # Click Send button
        send_btn = page.locator(
            "button.msg-form__send-button, "
            "button[type='submit'].msg-form__send-button"
        )
        if await send_btn.count() == 0:
            send_btn = page.locator("button").filter(has_text="Send").last
        if await send_btn.count() == 0:
            send_btn = page.locator("button[aria-label*='Send']").last

        if await send_btn.count() > 0:
            await send_btn.click()
            await _random_pause(1.5, 3.0)
            logger.info("DM reply sent (%d chars)", len(reply_text))
            return True

        # Fallback: keyboard shortcut
        logger.warning("Send button not found, trying Enter")
        await page.keyboard.press("Enter")
        await _random_pause(1.5, 3.0)
        return True

    except Exception as e:
        logger.error("Failed to send DM reply: %s", e)
        return False


async def mark_conversation_read(page: Page) -> bool:
    """Mark the currently open conversation as read without sending a reply.

    Simply clicking into a conversation usually marks it as read on LinkedIn.
    This function just scrolls the message list to ensure read status.
    """
    try:
        msg_list = page.locator(
            "ul.msg-s-message-list-content, "
            "div.msg-s-message-list-container"
        )
        if await msg_list.count() > 0:
            await msg_list.first.scroll_into_view_if_needed()
            await _random_pause(0.5, 1.0)
        return True
    except Exception:
        return True  # Best effort — clicking into the thread usually suffices


# ---------------------------------------------------------------------------
# Direct Messaging with Audio Attachment
# ---------------------------------------------------------------------------

async def open_dm_and_send_audio(
    page: Page,
    profile_url: str,
    audio_path: str,
    text_message: str = "",
) -> bool:
    """Open a DM conversation with a person and send an audio file.

    Args:
        page: Playwright page.
        profile_url: LinkedIn profile URL of the recipient.
        audio_path: Local path to the audio file to attach.
        text_message: Optional text message to accompany the audio.

    Returns True if the message was sent successfully.
    """
    try:
        import os
        if not os.path.exists(audio_path):
            logger.error("Audio file not found: %s", audio_path)
            return False

        # Navigate to profile and click "Message" button
        url = profile_url.rstrip("/") + "/"
        await page.goto(url, wait_until="domcontentloaded")
        if await check_for_challenge(page):
            raise LinkedInChallengeDetected("Challenge on profile for DM")
        await _random_pause(2.0, 3.0)

        # Click Message button
        msg_btn = page.get_by_role("button", name="Message")
        if await msg_btn.count() == 0:
            msg_btn = page.locator("button").filter(has_text="Message").first
        if await msg_btn.count() == 0:
            logger.error("Message button not found on %s", profile_url)
            return False

        await msg_btn.click()
        await _random_pause(2.0, 3.0)

        # Attach the audio file
        # LinkedIn's message compose has an attachment button (paperclip icon)
        attach_btn = page.locator(
            "button[aria-label*='Attach'], "
            "button[aria-label*='attach'], "
            "button[aria-label*='Add a file']"
        )

        if await attach_btn.count() > 0:
            # LinkedIn uses a hidden file input — set files on it
            file_input = page.locator("input[type='file']")
            if await file_input.count() > 0:
                await file_input.set_input_files(audio_path)
                await _random_pause(2.0, 4.0)
            else:
                # Click the attach button to trigger file dialog
                await attach_btn.first.click()
                await _random_pause(1.0, 2.0)
                file_input = page.locator("input[type='file']")
                if await file_input.count() > 0:
                    await file_input.set_input_files(audio_path)
                    await _random_pause(2.0, 4.0)

        # Type text message if provided
        if text_message:
            msg_box = page.locator("div[role='textbox']").last
            if await msg_box.count() > 0:
                await human_type_into_element(page, msg_box, text_message)
                await _random_pause(0.5, 1.0)

        # Send the message
        send_btn = page.locator("button").filter(has_text="Send").last
        if await send_btn.count() == 0:
            send_btn = page.locator("button[aria-label*='Send']").last
        if await send_btn.count() > 0:
            await send_btn.click()
            await _random_pause(2.0, 4.0)
            logger.info("DM with audio sent to %s", profile_url)
            return True

        logger.error("Send button not found for DM to %s", profile_url)
        return False

    except LinkedInChallengeDetected:
        raise
    except Exception as e:
        logger.error("Failed to send DM with audio to %s: %s", profile_url, e)
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _random_pause(min_sec: float, max_sec: float) -> None:
    """Sleep for a random duration to simulate human behavior."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))
