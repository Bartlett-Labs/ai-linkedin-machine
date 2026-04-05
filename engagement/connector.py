"""
Auto-connection engine — grows Kyle's LinkedIn network automatically.

Two modes:
1. Commenter auto-connect: Anyone who comments on Kyle's posts gets a
   personalized connection request (highest priority).
2. Outbound search connect: Search LinkedIn for relevant people by keywords,
   location, and industry. Send personalized notes using LLM-researched profiles.

Daily budget is ~25 requests on LinkedIn Premium. Commenters always go first,
remaining budget goes to outbound search.

Connection tracker at tracking/linkedin/connections.json prevents duplicates.
"""

import asyncio
import json
import logging
import os
import random
from datetime import datetime, date
from typing import Optional

import yaml

from browser.context_manager import PersonaContext
from browser.linkedin_actions import (
    accept_pending_invitations,
    get_feed_posts,
    get_post_comments,
    get_profile_info,
    navigate_to_feed,
    search_linkedin_people,
    send_connection_request,
    LinkedInChallengeDetected,
)
from config import load_personas
from llm.provider import generate_connection_note
from summarization.safety_filter import violates_safety
from utils import project_path
from utils.kill_switch import check_kill_switch, activate_kill_switch

logger = logging.getLogger(__name__)

CONFIG_PATH = project_path("config", "connector.yaml")
TRACKER_PATH = project_path("tracking", "linkedin", "connections.json")


def _load_config() -> dict:
    """Load connector configuration from YAML."""
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def _load_tracker() -> dict:
    """Load the connection request tracker."""
    if os.path.exists(TRACKER_PATH):
        with open(TRACKER_PATH, "r") as f:
            return json.load(f)
    return {
        "requests_sent": [],
        "daily_counts": {},
    }


def _save_tracker(tracker: dict) -> None:
    """Persist the connection tracker to disk."""
    os.makedirs(os.path.dirname(TRACKER_PATH), exist_ok=True)
    with open(TRACKER_PATH, "w") as f:
        json.dump(tracker, f, indent=2)


def _get_today_count(tracker: dict) -> int:
    """How many connection requests were sent today."""
    today = date.today().isoformat()
    return tracker.get("daily_counts", {}).get(today, 0)


def _increment_today(tracker: dict) -> None:
    """Bump today's count by one."""
    today = date.today().isoformat()
    if "daily_counts" not in tracker:
        tracker["daily_counts"] = {}
    tracker["daily_counts"][today] = tracker["daily_counts"].get(today, 0) + 1


def _is_already_tracked(tracker: dict, profile_url: str) -> bool:
    """Check if we've already sent a request to this profile."""
    tracked_urls = {r["profile_url"] for r in tracker.get("requests_sent", [])}
    # Normalize URL — strip trailing slash and query params
    normalized = profile_url.rstrip("/").split("?")[0]
    return any(
        t.rstrip("/").split("?")[0] == normalized
        for t in tracked_urls
    )


async def run_connector(
    max_requests: int = 0,
    headless: bool = True,
    dry_run: bool = False,
    commenter_only: bool = False,
    outbound_only: bool = False,
) -> dict:
    """Run the auto-connection engine.

    Args:
        max_requests: Override daily limit (0 = use config).
        headless: Run browser headless.
        dry_run: Generate notes but don't send requests.
        commenter_only: Only connect with commenters on Kyle's posts.
        outbound_only: Only do outbound search connections.

    Returns:
        Summary dict with counts and details.
    """
    config = _load_config()
    tracker = _load_tracker()

    daily_limit = max_requests or config.get("daily_limit", 25)
    sent_today = _get_today_count(tracker)
    remaining = daily_limit - sent_today

    summary = {
        "commenter_connects": 0,
        "outbound_connects": 0,
        "invitations_accepted": 0,
        "skipped_already_tracked": 0,
        "skipped_safety": 0,
        "errors": [],
        "daily_total": sent_today,
        "daily_limit": daily_limit,
        "dry_run": dry_run,
    }

    if remaining <= 0:
        logger.info("Daily connection limit reached (%d/%d)", sent_today, daily_limit)
        return summary

    logger.info(
        "Starting connector: %d/%d sent today, %d remaining",
        sent_today, daily_limit, remaining,
    )

    # Load MainUser persona for system prompt
    personas = load_personas()
    main_user = next((p for p in personas if p["name"] == "MainUser"), personas[0])

    async with PersonaContext("MainUser", headless=headless) as ctx:
        page = await ctx.new_page()

        # Phase 0: Auto-accept pending invitations (no budget cost)
        try:
            if dry_run:
                logger.info("[DRY RUN] Would auto-accept pending invitations")
            else:
                accepted = await accept_pending_invitations(page, max_accepts=50)
                summary["invitations_accepted"] = len(accepted)
                # Track accepted invitations
                if accepted:
                    if "invitations_accepted" not in tracker:
                        tracker["invitations_accepted"] = []
                    for inv in accepted:
                        tracker["invitations_accepted"].append({
                            "name": inv.get("name", ""),
                            "profile_url": inv.get("profile_url", ""),
                            "headline": inv.get("headline", ""),
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                    logger.info("Auto-accepted %d invitations", len(accepted))
        except LinkedInChallengeDetected as e:
            logger.error("Challenge during auto-accept: %s", e)
            activate_kill_switch(f"LinkedIn challenge during auto-accept: {e}")
            summary["errors"].append(f"Challenge: {e}")
            _save_tracker(tracker)
            return summary
        except Exception as e:
            logger.error("Auto-accept failed: %s", e)
            summary["errors"].append(f"Auto-accept error: {e}")

        if check_kill_switch():
            _save_tracker(tracker)
            return summary

        # Phase 1: Commenter auto-connect (priority)
        if not outbound_only and config.get("commenter_priority", True):
            commenter_count = await _auto_connect_commenters(
                page, main_user, tracker, config, remaining, dry_run, summary,
            )
            remaining -= commenter_count

        if check_kill_switch():
            _save_tracker(tracker)
            return summary

        # Phase 2: Outbound search connect (remaining budget)
        if not commenter_only and remaining > 0:
            await _outbound_search_connect(
                page, main_user, tracker, config, remaining, dry_run, summary,
            )

    # Persist tracker
    if not dry_run:
        _save_tracker(tracker)

    summary["daily_total"] = _get_today_count(tracker)
    logger.info("Connector complete: %s", summary)
    return summary


async def _auto_connect_commenters(
    page,
    persona: dict,
    tracker: dict,
    config: dict,
    budget: int,
    dry_run: bool,
    summary: dict,
) -> int:
    """Find people who commented on Kyle's posts and send connection requests.

    Returns number of connection requests sent.
    """
    sent = 0
    rate_config = config.get("rate_limiting", {})
    min_delay = rate_config.get("min_delay_between_requests_sec", 45)
    max_delay = rate_config.get("max_delay_between_requests_sec", 90)

    try:
        # Navigate to Kyle's recent activity
        await page.goto(
            "https://www.linkedin.com/in/me/recent-activity/all/",
            wait_until="domcontentloaded",
        )
        await asyncio.sleep(random.uniform(2.0, 4.0))

        posts = await get_feed_posts(page, max_posts=10)
        if not posts:
            logger.info("No posts found on Kyle's activity page")
            return 0

        logger.info("Found %d posts to scan for commenters", len(posts))

        for post in posts:
            if sent >= budget or check_kill_switch():
                break

            try:
                comments = await get_post_comments(page, post["element_index"])
            except Exception as e:
                logger.warning("Could not get comments for post %d: %s", post["element_index"], e)
                continue

            for comment in comments:
                if sent >= budget or check_kill_switch():
                    break

                commenter_name = comment.get("author", "")
                profile_url = comment.get("profile_url", "")

                if not profile_url or not commenter_name:
                    continue

                # Skip self
                main_name = persona.get("display_name", "Kyle Bartlett")
                if commenter_name.lower() in (main_name.lower(), "kyle bartlett", "kyle"):
                    continue

                # Skip already tracked
                if _is_already_tracked(tracker, profile_url):
                    summary["skipped_already_tracked"] += 1
                    continue

                # Scrape their profile for personalization
                profile_info = await get_profile_info(page, profile_url)
                if not profile_info:
                    logger.warning("Could not scrape profile for %s", commenter_name)
                    continue

                # Generate personalized connection note via LLM
                note = generate_connection_note(
                    profile_info=profile_info,
                    persona_system_prompt=persona.get("system_prompt", ""),
                    context=f"They commented on your LinkedIn post: \"{post['text'][:200]}\"",
                )

                if not note:
                    logger.warning("LLM failed to generate note for %s", commenter_name)
                    continue

                # Safety check
                if violates_safety(note):
                    logger.warning("Connection note for %s blocked by safety filter", commenter_name)
                    summary["skipped_safety"] += 1
                    continue

                # Send or dry-run
                if dry_run:
                    logger.info(
                        "[DRY RUN] Would connect with commenter %s: %s",
                        commenter_name, note[:80],
                    )
                else:
                    success = await send_connection_request(page, profile_url, note)
                    if not success:
                        logger.error("Failed to send connection request to %s", commenter_name)
                        summary["errors"].append(f"Failed: {commenter_name}")
                        continue

                # Track
                tracker["requests_sent"].append({
                    "name": commenter_name,
                    "profile_url": profile_url,
                    "headline": profile_info.get("headline", ""),
                    "note": note,
                    "source": "commenter",
                    "post_context": post["text"][:100],
                    "timestamp": datetime.utcnow().isoformat(),
                    "dry_run": dry_run,
                })
                if not dry_run:
                    _increment_today(tracker)

                sent += 1
                summary["commenter_connects"] += 1
                logger.info("Connected with commenter: %s (%d/%d)", commenter_name, sent, budget)

                # Human-like delay
                delay = random.randint(min_delay, max_delay)
                logger.debug("Waiting %d seconds before next request", delay)
                await asyncio.sleep(delay)

    except LinkedInChallengeDetected as e:
        logger.error("Challenge detected during commenter connect: %s", e)
        activate_kill_switch(f"LinkedIn challenge during connector: {e}")
        summary["errors"].append(f"Challenge: {e}")
    except Exception as e:
        logger.error("Error in commenter auto-connect: %s", e)
        summary["errors"].append(f"Commenter connect error: {e}")

    return sent


async def _outbound_search_connect(
    page,
    persona: dict,
    tracker: dict,
    config: dict,
    budget: int,
    dry_run: bool,
    summary: dict,
) -> int:
    """Search LinkedIn for relevant people and send connection requests.

    Returns number of connection requests sent.
    """
    sent = 0
    search_config = config.get("search", {})
    rate_config = config.get("rate_limiting", {})
    min_delay = rate_config.get("min_delay_between_requests_sec", 45)
    max_delay = rate_config.get("max_delay_between_requests_sec", 90)
    search_delay = rate_config.get("min_delay_between_searches_sec", 120)
    max_per_search = rate_config.get("max_profiles_per_search", 10)

    keywords = search_config.get("keywords", [])
    title_keywords = search_config.get("title_keywords", [])
    location = search_config.get("location", "United States")

    if not keywords:
        logger.warning("No search keywords configured, skipping outbound")
        return 0

    # Shuffle keywords so we don't always search the same order
    random.shuffle(keywords)

    for keyword in keywords:
        if sent >= budget or check_kill_switch():
            break

        try:
            # Build search query with location
            query = f"{keyword} {location}"
            logger.info("Searching LinkedIn for: %s", query)

            people = await search_linkedin_people(page, query, max_results=max_per_search)
            if not people:
                logger.info("No results for query: %s", query)
                await asyncio.sleep(random.uniform(3, 8))
                continue

            logger.info("Found %d people for '%s'", len(people), keyword)

            # Score and filter candidates
            scored = _score_candidates(people, title_keywords)

            for candidate in scored:
                if sent >= budget or check_kill_switch():
                    break

                profile_url = candidate.get("profile_url", "")
                name = candidate.get("name", "")

                if not profile_url or not name:
                    continue

                # Skip already tracked
                if _is_already_tracked(tracker, profile_url):
                    summary["skipped_already_tracked"] += 1
                    continue

                # Get full profile info for personalization
                profile_info = await get_profile_info(page, profile_url)
                if not profile_info:
                    continue

                # Generate personalized connection note
                note = generate_connection_note(
                    profile_info=profile_info,
                    persona_system_prompt=persona.get("system_prompt", ""),
                    context=f"Found via search for '{keyword}'. Potential shared interest in {keyword}.",
                )

                if not note:
                    continue

                # Safety check
                if violates_safety(note):
                    summary["skipped_safety"] += 1
                    continue

                # Send or dry-run
                if dry_run:
                    logger.info(
                        "[DRY RUN] Would connect with %s (%s): %s",
                        name, candidate.get("headline", ""), note[:80],
                    )
                else:
                    success = await send_connection_request(page, profile_url, note)
                    if not success:
                        summary["errors"].append(f"Failed: {name}")
                        continue

                # Track
                tracker["requests_sent"].append({
                    "name": name,
                    "profile_url": profile_url,
                    "headline": profile_info.get("headline", ""),
                    "note": note,
                    "source": "outbound_search",
                    "search_keyword": keyword,
                    "relevance_score": candidate.get("score", 0),
                    "timestamp": datetime.utcnow().isoformat(),
                    "dry_run": dry_run,
                })
                if not dry_run:
                    _increment_today(tracker)

                sent += 1
                summary["outbound_connects"] += 1
                logger.info(
                    "Connected with %s (score=%d, %d/%d)",
                    name, candidate.get("score", 0), sent, budget,
                )

                # Human-like delay
                delay = random.randint(min_delay, max_delay)
                await asyncio.sleep(delay)

            # Delay between searches
            await asyncio.sleep(random.randint(search_delay, search_delay + 60))

        except LinkedInChallengeDetected as e:
            logger.error("Challenge detected during outbound search: %s", e)
            activate_kill_switch(f"LinkedIn challenge during connector: {e}")
            summary["errors"].append(f"Challenge: {e}")
            break
        except Exception as e:
            logger.error("Error in outbound search for '%s': %s", keyword, e)
            summary["errors"].append(f"Search error ({keyword}): {e}")

    return sent


def _score_candidates(people: list[dict], title_keywords: list[str]) -> list[dict]:
    """Score and sort search results by title keyword relevance.

    Higher score = better match for Kyle's network.
    """
    title_lower = [kw.lower() for kw in title_keywords]

    for person in people:
        score = 0
        headline = (person.get("headline") or "").lower()

        # Title keyword matches
        for kw in title_lower:
            if kw in headline:
                score += 10

        # Mutual connections boost
        mutuals = person.get("mutual_connections", 0)
        if mutuals:
            score += min(mutuals * 2, 10)

        person["score"] = score

    # Sort by score descending, then by mutual connections
    people.sort(key=lambda p: (p.get("score", 0), p.get("mutual_connections", 0)), reverse=True)
    return people


async def get_connector_status() -> dict:
    """Get current connector status for the API/dashboard."""
    tracker = _load_tracker()
    config = _load_config()

    today = date.today().isoformat()
    sent_today = tracker.get("daily_counts", {}).get(today, 0)
    daily_limit = config.get("daily_limit", 25)

    # Count by source
    today_requests = [
        r for r in tracker.get("requests_sent", [])
        if r.get("timestamp", "").startswith(today)
    ]
    commenter_today = sum(1 for r in today_requests if r.get("source") == "commenter")
    outbound_today = sum(1 for r in today_requests if r.get("source") == "outbound_search")

    # Invitation acceptance stats
    all_accepted = tracker.get("invitations_accepted", [])
    accepted_today = sum(
        1 for a in all_accepted
        if a.get("timestamp", "").startswith(today)
    )

    return {
        "sent_today": sent_today,
        "daily_limit": daily_limit,
        "remaining": max(0, daily_limit - sent_today),
        "commenter_today": commenter_today,
        "outbound_today": outbound_today,
        "accepted_today": accepted_today,
        "total_accepted": len(all_accepted),
        "total_all_time": len(tracker.get("requests_sent", [])),
        "config": {
            "commenter_priority": config.get("commenter_priority", True),
            "search_keywords": config.get("search", {}).get("keywords", []),
            "location": config.get("search", {}).get("location", ""),
        },
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LinkedIn Auto-Connection Engine")
    parser.add_argument("--dry-run", action="store_true", help="Generate notes without sending")
    parser.add_argument("--commenter-connect", action="store_true", help="Only connect with commenters")
    parser.add_argument("--outbound", action="store_true", help="Only do outbound search connections")
    parser.add_argument("--max", type=int, default=0, help="Override daily limit")
    parser.add_argument("--no-headless", action="store_true", help="Show browser window")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    result = asyncio.run(
        run_connector(
            max_requests=args.max,
            headless=not args.no_headless,
            dry_run=args.dry_run,
            commenter_only=args.commenter_connect,
            outbound_only=args.outbound,
        )
    )
    print(json.dumps(result, indent=2))
