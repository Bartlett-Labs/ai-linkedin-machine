"""
ElevenLabs voice follow-up for new LinkedIn connections.

After a connection request is accepted, generates a personalized voice message
using Kyle's cloned voice via ElevenLabs TTS, then sends it as a DM via
Playwright browser automation.

Flow:
1. Monitor My Network page for newly accepted connections
2. Cross-reference against connection tracker to find pending follow-ups
3. LLM generates a personalized 30-60 second voice script
4. ElevenLabs converts script to audio (Kyle's cloned voice)
5. Playwright sends audio as DM attachment + optional text

Configurable delay (default 2 hours) between acceptance and DM to avoid
seeming overly eager or automated.
"""

import asyncio
import json
import logging
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import yaml

from browser.context_manager import PersonaContext
from browser.linkedin_actions import (
    get_new_connections,
    get_profile_info,
    open_dm_and_send_audio,
    LinkedInChallengeDetected,
)
from config import load_personas
from llm.provider import generate_voice_script
from summarization.safety_filter import violates_safety
from utils import project_path
from utils.kill_switch import check_kill_switch, activate_kill_switch

logger = logging.getLogger(__name__)

CONFIG_PATH = project_path("config", "connector.yaml")
TRACKER_PATH = project_path("tracking", "linkedin", "connections.json")
VOICE_DIR = project_path("tracking", "linkedin", "voice_messages")


def _load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def _load_tracker() -> dict:
    if os.path.exists(TRACKER_PATH):
        with open(TRACKER_PATH, "r") as f:
            return json.load(f)
    return {"requests_sent": [], "daily_counts": {}, "voice_sent": []}


def _save_tracker(tracker: dict) -> None:
    os.makedirs(os.path.dirname(TRACKER_PATH), exist_ok=True)
    with open(TRACKER_PATH, "w") as f:
        json.dump(tracker, f, indent=2)


def _generate_audio(script: str, voice_config: dict, output_path: str) -> bool:
    """Convert script text to audio via ElevenLabs TTS.

    Args:
        script: The voice message script text.
        voice_config: Dict with voice_id, model, stability, similarity_boost.
        output_path: Where to save the MP3 file.

    Returns:
        True if audio was generated successfully.
    """
    voice_id = voice_config.get("voice_id") or os.getenv("ELEVENLABS_VOICE_ID")
    if not voice_id:
        logger.error("No ElevenLabs voice_id configured (set ELEVENLABS_VOICE_ID or config voice.voice_id)")
        return False

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        logger.error("ELEVENLABS_API_KEY not set")
        return False

    try:
        from elevenlabs import ElevenLabs

        client = ElevenLabs(api_key=api_key)

        audio_iterator = client.text_to_speech.convert(
            voice_id=voice_id,
            text=script,
            model_id=voice_config.get("model", "eleven_multilingual_v2"),
            voice_settings={
                "stability": voice_config.get("stability", 0.5),
                "similarity_boost": voice_config.get("similarity_boost", 0.8),
            },
        )

        # Write audio chunks to file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in audio_iterator:
                f.write(chunk)

        file_size = os.path.getsize(output_path)
        logger.info("Generated voice audio: %s (%d bytes)", output_path, file_size)
        return file_size > 0

    except ImportError:
        logger.error("elevenlabs package not installed: pip install elevenlabs")
        return False
    except Exception as e:
        logger.error("ElevenLabs TTS failed: %s", e)
        return False


async def monitor_and_send_voice(
    headless: bool = True,
    dry_run: bool = False,
    max_messages: int = 10,
) -> dict:
    """Check for new connection acceptances and send voice follow-ups.

    Args:
        headless: Run browser headless.
        dry_run: Generate scripts/audio but don't send DMs.
        max_messages: Maximum voice messages to send per run.

    Returns:
        Summary dict with counts.
    """
    config = _load_config()
    tracker = _load_tracker()
    voice_config = config.get("voice", {})
    rate_config = config.get("rate_limiting", {})
    delay_hours = rate_config.get("voice_delay_after_acceptance_hours", 2)

    summary = {
        "new_acceptances": 0,
        "voice_messages_sent": 0,
        "skipped_too_recent": 0,
        "skipped_already_sent": 0,
        "errors": [],
        "dry_run": dry_run,
    }

    # Set of profiles we've already sent voice messages to
    voice_sent_urls = {
        v["profile_url"]
        for v in tracker.get("voice_sent", [])
    }

    # Load MainUser persona
    personas = load_personas()
    main_user = next((p for p in personas if p["name"] == "MainUser"), personas[0])

    async with PersonaContext("MainUser", headless=headless) as ctx:
        page = await ctx.new_page()

        # Get recently accepted connections from My Network
        try:
            new_connections = await get_new_connections(page, max_results=20)
        except Exception as e:
            logger.error("Failed to get new connections: %s", e)
            summary["errors"].append(f"Get connections failed: {e}")
            return summary

        if not new_connections:
            logger.info("No new connections found")
            return summary

        summary["new_acceptances"] = len(new_connections)
        logger.info("Found %d new/recent connections", len(new_connections))

        sent = 0
        for conn in new_connections:
            if sent >= max_messages or check_kill_switch():
                break

            profile_url = conn.get("profile_url", "")
            name = conn.get("name", "")

            if not profile_url:
                continue

            # Skip if already sent voice message
            normalized = profile_url.rstrip("/").split("?")[0]
            if normalized in voice_sent_urls or any(
                v.rstrip("/").split("?")[0] == normalized for v in voice_sent_urls
            ):
                summary["skipped_already_sent"] += 1
                continue

            # Check if this was one of our tracked connection requests
            matching_request = None
            for req in tracker.get("requests_sent", []):
                req_url = req.get("profile_url", "").rstrip("/").split("?")[0]
                if req_url == normalized:
                    matching_request = req
                    break

            # Respect delay — don't DM too soon after acceptance
            if matching_request:
                sent_time = matching_request.get("timestamp", "")
                if sent_time:
                    try:
                        sent_dt = datetime.fromisoformat(sent_time)
                        min_dm_time = sent_dt + timedelta(hours=delay_hours)
                        if datetime.utcnow() < min_dm_time:
                            summary["skipped_too_recent"] += 1
                            logger.debug(
                                "Skipping %s — too soon (wait until %s)",
                                name, min_dm_time.isoformat(),
                            )
                            continue
                    except (ValueError, TypeError):
                        pass

            # Get full profile info for personalization
            profile_info = await get_profile_info(page, profile_url)
            if not profile_info:
                logger.warning("Could not scrape profile for voice message: %s", name)
                continue

            # Generate voice script via LLM
            script = generate_voice_script(
                profile_info=profile_info,
                persona_system_prompt=main_user.get("system_prompt", ""),
            )
            if not script:
                logger.warning("Failed to generate voice script for %s", name)
                continue

            # Safety check the script
            if violates_safety(script):
                logger.warning("Voice script for %s blocked by safety filter", name)
                summary["errors"].append(f"Safety blocked: {name}")
                continue

            # Generate audio via ElevenLabs
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c for c in name if c.isalnum() or c in " _-").strip().replace(" ", "_")
            audio_filename = f"{timestamp}_{safe_name}.mp3"
            audio_path = os.path.join(VOICE_DIR, audio_filename)

            if dry_run:
                logger.info(
                    "[DRY RUN] Would generate voice message for %s:\n  Script: %s",
                    name, script[:120],
                )
            else:
                audio_ok = _generate_audio(script, voice_config, audio_path)
                if not audio_ok:
                    logger.error("Failed to generate audio for %s", name)
                    summary["errors"].append(f"Audio generation failed: {name}")
                    continue

                # Send DM with audio attachment
                try:
                    text_fallback = f"Hey {profile_info.get('name', '').split()[0]}, thanks for connecting! Sent you a quick voice note."
                    dm_ok = await open_dm_and_send_audio(
                        page, profile_url, audio_path, text_fallback,
                    )
                    if not dm_ok:
                        logger.error("Failed to send voice DM to %s", name)
                        summary["errors"].append(f"DM send failed: {name}")
                        continue
                except LinkedInChallengeDetected as e:
                    logger.error("Challenge during voice DM: %s", e)
                    activate_kill_switch(f"LinkedIn challenge during voice outreach: {e}")
                    summary["errors"].append(f"Challenge: {e}")
                    break

            # Track
            voice_record = {
                "name": name,
                "profile_url": profile_url,
                "script": script,
                "audio_file": audio_filename if not dry_run else None,
                "timestamp": datetime.utcnow().isoformat(),
                "dry_run": dry_run,
            }

            if "voice_sent" not in tracker:
                tracker["voice_sent"] = []
            tracker["voice_sent"].append(voice_record)
            voice_sent_urls.add(normalized)

            sent += 1
            summary["voice_messages_sent"] += 1
            logger.info("Voice message %s to %s (%d/%d)",
                        "generated" if dry_run else "sent", name, sent, max_messages)

            # Delay between DMs
            if not dry_run:
                delay = random.randint(60, 180)
                await asyncio.sleep(delay)

    # Persist
    if not dry_run:
        _save_tracker(tracker)

    logger.info("Voice outreach complete: %s", summary)
    return summary


async def test_voice_generation(text: str = "") -> Optional[str]:
    """Generate a test audio file. Returns path to the file or None."""
    config = _load_config()
    voice_config = config.get("voice", {})

    if not text:
        text = (
            "Hey, this is a test of the voice message system. "
            "If you're hearing this, the ElevenLabs integration is working correctly. "
            "The audio quality should sound natural and conversational."
        )

    os.makedirs(VOICE_DIR, exist_ok=True)
    output_path = os.path.join(VOICE_DIR, "test_voice.mp3")
    success = _generate_audio(text, voice_config, output_path)
    return output_path if success else None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LinkedIn Voice Outreach")
    parser.add_argument("--dry-run", action="store_true", help="Generate scripts without sending")
    parser.add_argument("--test", action="store_true", help="Generate a test audio file")
    parser.add_argument("--max", type=int, default=10, help="Max voice messages per run")
    parser.add_argument("--no-headless", action="store_true", help="Show browser")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    if args.test:
        path = asyncio.run(test_voice_generation())
        if path:
            print(f"Test audio saved to: {path}")
        else:
            print("Test failed — check ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID")
    else:
        result = asyncio.run(
            monitor_and_send_voice(
                headless=not args.no_headless,
                dry_run=args.dry_run,
                max_messages=args.max,
            )
        )
        print(json.dumps(result, indent=2))
