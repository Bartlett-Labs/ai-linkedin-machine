"""
Seed script: Import data from Google Sheets + config files → Postgres.

Usage:
    python -m db.seed              # from project root
    python db/seed.py              # or directly

Reads ALL tabs from the Google Sheet, maps rows to SQLAlchemy models,
and inserts them into the corresponding Postgres tables.
Also imports config/feeds.json → feed_sources table.

Safe to run multiple times — truncates tables first (except pipeline_runs).
"""

import json
import logging
import os
import sys
from pathlib import Path

# Ensure project root on sys.path
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from dotenv import load_dotenv
load_dotenv(_root / ".env")

from sqlalchemy import text

from db.engine import get_sync_engine, sync_session
from db import models as m

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


def _import_sheets():
    """Import data from Google Sheets via SheetsClient."""
    try:
        from sheets.client import SheetsClient
    except Exception as e:
        logger.warning("Could not import SheetsClient: %s", e)
        logger.warning("Skipping Google Sheets import. Tables will be empty.")
        return

    try:
        sc = SheetsClient()
    except Exception as e:
        logger.warning("Could not connect to Google Sheets: %s", e)
        logger.warning("Skipping Google Sheets import. Tables will be empty.")
        return

    logger.info("Connected to Google Sheets — importing data...")

    # --- EngineControl (singleton) ---
    try:
        ec = sc.get_engine_control()
        with sync_session() as session:
            row = session.get(m.EngineControl, 1)
            if row is None:
                row = m.EngineControl(id=1)
                session.add(row)
            row.mode = ec.mode.value
            row.phase = ec.phase.value
            row.main_user_posting = ec.main_user_posting
            row.phantom_engagement = ec.phantom_engagement
            row.commenting = ec.commenting
            row.replying = ec.replying
            row.last_run = ec.last_run
        logger.info("  EngineControl: imported")
    except Exception as e:
        logger.error("  EngineControl failed: %s", e)

    # --- ScheduleConfigs ---
    try:
        configs = sc.get_schedule_configs()
        with sync_session() as session:
            session.execute(text("TRUNCATE TABLE schedule_configs RESTART IDENTITY CASCADE"))
            for cfg in configs:
                session.add(m.ScheduleConfig(
                    phase=cfg.mode,
                    posts_per_week=cfg.posts_per_week,
                    comments_per_day_min=cfg.comments_per_day_min,
                    comments_per_day_max=cfg.comments_per_day_max,
                    phantom_comments_min=cfg.phantom_comments_min,
                    phantom_comments_max=cfg.phantom_comments_max,
                    min_delay_sec=cfg.min_delay_sec,
                    max_likes_per_day=cfg.max_likes_per_day,
                ))
        logger.info("  ScheduleConfigs: %d rows", len(configs))
    except Exception as e:
        logger.error("  ScheduleConfigs failed: %s", e)

    # --- SafetyTerms ---
    try:
        terms = sc.get_safety_terms()
        with sync_session() as session:
            session.execute(text("TRUNCATE TABLE safety_terms RESTART IDENTITY CASCADE"))
            for t in terms:
                session.add(m.SafetyTerm(term=t.term, response=t.response))
        logger.info("  SafetyTerms: %d rows", len(terms))
    except Exception as e:
        logger.error("  SafetyTerms failed: %s", e)

    # --- ReplyRules ---
    try:
        rules = sc.get_reply_rules()
        with sync_session() as session:
            session.execute(text("TRUNCATE TABLE reply_rules RESTART IDENTITY CASCADE"))
            for r in rules:
                session.add(m.ReplyRule(
                    condition_type=r.condition_type,
                    trigger=r.trigger,
                    action=r.action.value,
                    notes=r.notes,
                ))
        logger.info("  ReplyRules: %d rows", len(rules))
    except Exception as e:
        logger.error("  ReplyRules failed: %s", e)

    # --- CommentTargets ---
    try:
        targets = sc.get_comment_targets()
        with sync_session() as session:
            session.execute(text("TRUNCATE TABLE comment_targets RESTART IDENTITY CASCADE"))
            for t in targets:
                session.add(m.CommentTarget(
                    name=t.name,
                    linkedin_url=t.linkedin_url,
                    category=t.category,
                    priority=t.priority,
                    last_comment_date=t.last_comment_date,
                    notes=t.notes,
                ))
        logger.info("  CommentTargets: %d rows", len(targets))
    except Exception as e:
        logger.error("  CommentTargets failed: %s", e)

    # --- CommentTemplates ---
    try:
        templates = sc.get_comment_templates(persona="")
        with sync_session() as session:
            session.execute(text("TRUNCATE TABLE comment_templates RESTART IDENTITY CASCADE"))
            for t in templates:
                session.add(m.CommentTemplate(
                    template_text=t.template_text,
                    tone=t.tone,
                    category=t.category,
                    safety_flag=t.safety_flag,
                    example_use=t.example_use,
                    persona=t.persona,
                    use_count=t.use_count,
                ))
        logger.info("  CommentTemplates: %d rows", len(templates))
    except Exception as e:
        logger.error("  CommentTemplates failed: %s", e)

    # --- ContentBank ---
    try:
        items = sc.get_content_bank(ready_only=False)
        with sync_session() as session:
            session.execute(text("TRUNCATE TABLE content_bank RESTART IDENTITY CASCADE"))
            for item in items:
                session.add(m.ContentBank(
                    category=item.category,
                    post_type=item.post_type,
                    draft=item.draft,
                    safety_flag=item.safety_flag,
                    ready=item.ready,
                    last_used=item.last_used,
                    notes=item.notes,
                ))
        logger.info("  ContentBank: %d rows", len(items))
    except Exception as e:
        logger.error("  ContentBank failed: %s", e)

    # --- RepostBank ---
    try:
        items = sc.get_repost_bank()
        with sync_session() as session:
            session.execute(text("TRUNCATE TABLE repost_bank RESTART IDENTITY CASCADE"))
            for item in items:
                session.add(m.RepostBank(
                    source_name=item.source_name,
                    source_url=item.source_url,
                    summary=item.summary,
                    commentary_prompt=item.commentary_prompt,
                    safety_flag=item.safety_flag,
                    last_used=item.last_used,
                    notes=item.notes,
                ))
        logger.info("  RepostBank: %d rows", len(items))
    except Exception as e:
        logger.error("  RepostBank failed: %s", e)

    # --- ActivityWindows ---
    try:
        windows = sc.get_activity_windows()
        with sync_session() as session:
            session.execute(text("TRUNCATE TABLE activity_windows RESTART IDENTITY CASCADE"))
            for w in windows:
                session.add(m.ActivityWindow(
                    window_name=w.window_name,
                    start_hour=w.start_hour,
                    end_hour=w.end_hour,
                    days_of_week=w.days_of_week,
                    enabled=w.enabled,
                ))
        logger.info("  ActivityWindows: %d rows", len(windows))
    except Exception as e:
        logger.error("  ActivityWindows failed: %s", e)

    # --- OutboundQueue ---
    try:
        ready = sc.get_ready_items(limit=500)
        with sync_session() as session:
            # Don't truncate — preserve any existing queue items
            for item in ready:
                session.add(m.OutboundQueue(
                    post_id=item.post_id,
                    action_type=item.content_type,
                    persona=item.persona,
                    draft_text=item.content,
                    target_url=item.target_url,
                    status=item.status.value,
                    notes=item.notes or "",
                ))
        logger.info("  OutboundQueue: %d READY items imported", len(ready))
    except Exception as e:
        logger.error("  OutboundQueue failed: %s", e)

    # --- SystemLog (recent entries only — don't import full history) ---
    try:
        header, data, total = sc.get_tab_data("SystemLog", "A:G")
        recent = data[-100:] if len(data) > 100 else data
        with sync_session() as session:
            for row in recent:
                # Columns: Timestamp, Module, Action, Target, Result, Safety, Notes
                padded = row + [""] * (7 - len(row))
                session.add(m.SystemLog(
                    module=padded[1],
                    action=padded[2],
                    target=padded[3],
                    result=padded[4],
                    safety=padded[5] or "Safe",
                    notes=padded[6],
                ))
        logger.info("  SystemLog: %d recent entries imported (of %d total)", len(recent), total)
    except Exception as e:
        logger.error("  SystemLog failed: %s", e)


def _import_feeds():
    """Import config/feeds.json → feed_sources table."""
    feeds_path = _root / "config" / "feeds.json"
    if not feeds_path.exists():
        logger.warning("config/feeds.json not found, skipping feed import")
        return

    with open(feeds_path) as f:
        data = json.load(f)

    sources = data.get("sources", [])
    with sync_session() as session:
        session.execute(text("TRUNCATE TABLE feed_sources RESTART IDENTITY CASCADE"))
        for src in sources:
            # Derive category from name
            name = src.get("name", "")
            category = "ai"
            if "techcrunch" in name.lower():
                category = "tech_news"
            elif "arxiv" in name.lower():
                category = "research"
            elif "github" in name.lower():
                category = "dev_tools"

            session.add(m.FeedSource(
                name=name,
                url=src.get("url", ""),
                feed_type=src.get("type", "rss"),
                category=category,
                active=True,
            ))

    logger.info("  FeedSources: %d feeds imported from config/feeds.json", len(sources))


def _ensure_defaults():
    """Ensure critical default rows exist."""
    with sync_session() as session:
        # EngineControl singleton
        ec = session.get(m.EngineControl, 1)
        if ec is None:
            session.add(m.EngineControl(
                id=1,
                mode=m.EngineModeEnum.DRY_RUN.value,
                phase=m.PhaseEnum.STEALTH.value,
            ))
            logger.info("  Created default EngineControl row")

    # Default schedule configs if none exist
    with sync_session() as session:
        count = session.execute(
            text("SELECT COUNT(*) FROM schedule_configs")
        ).scalar()
        if count == 0:
            defaults = [
                ("stealth", 2, 2, 4, 1, 2, 60, 15),
                ("announcement", 3, 3, 6, 2, 4, 45, 25),
                ("authority", 5, 5, 10, 3, 6, 30, 40),
            ]
            for phase, ppw, cdmin, cdmax, pcmin, pcmax, delay, likes in defaults:
                session.add(m.ScheduleConfig(
                    phase=phase,
                    posts_per_week=ppw,
                    comments_per_day_min=cdmin,
                    comments_per_day_max=cdmax,
                    phantom_comments_min=pcmin,
                    phantom_comments_max=pcmax,
                    min_delay_sec=delay,
                    max_likes_per_day=likes,
                ))
            logger.info("  Created default ScheduleConfigs for 3 phases")

    # Default activity windows if none exist
    with sync_session() as session:
        count = session.execute(
            text("SELECT COUNT(*) FROM activity_windows")
        ).scalar()
        if count == 0:
            windows = [
                ("Morning", 7, 9, "weekdays"),
                ("Lunch", 11, 13, "weekdays"),
                ("Evening", 17, 19, "weekdays"),
                ("Weekend Morning", 9, 11, "weekends"),
            ]
            for name, start, end, days in windows:
                session.add(m.ActivityWindow(
                    window_name=name,
                    start_hour=start,
                    end_hour=end,
                    days_of_week=days,
                    enabled=True,
                ))
            logger.info("  Created default ActivityWindows")


def main():
    logger.info("=" * 60)
    logger.info("AI LinkedIn Machine — Database Seed")
    logger.info("=" * 60)

    db_url = os.getenv("DATABASE_URL", "")
    logger.info("Database: %s", db_url.split("@")[-1] if "@" in db_url else db_url)

    # Step 1: Import from Google Sheets
    logger.info("")
    logger.info("Step 1: Import from Google Sheets")
    logger.info("-" * 40)
    _import_sheets()

    # Step 2: Import feeds.json
    logger.info("")
    logger.info("Step 2: Import config/feeds.json")
    logger.info("-" * 40)
    _import_feeds()

    # Step 3: Ensure defaults exist
    logger.info("")
    logger.info("Step 3: Ensure defaults")
    logger.info("-" * 40)
    _ensure_defaults()

    # Step 4: Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Seed complete! Summary:")
    logger.info("-" * 40)
    with sync_session() as session:
        tables = [
            ("engine_control", m.EngineControl),
            ("schedule_configs", m.ScheduleConfig),
            ("safety_terms", m.SafetyTerm),
            ("reply_rules", m.ReplyRule),
            ("comment_targets", m.CommentTarget),
            ("comment_templates", m.CommentTemplate),
            ("content_bank", m.ContentBank),
            ("repost_bank", m.RepostBank),
            ("activity_windows", m.ActivityWindow),
            ("outbound_queue", m.OutboundQueue),
            ("system_logs", m.SystemLog),
            ("feed_sources", m.FeedSource),
            ("pipeline_runs", m.PipelineRun),
        ]
        for name, model in tables:
            count = session.execute(
                text(f"SELECT COUNT(*) FROM {name}")
            ).scalar()
            logger.info("  %-25s %d rows", name, count)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
