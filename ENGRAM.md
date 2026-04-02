# ENGRAM — AI LinkedIn Machine

> Last updated: 2026-04-02T16:30 CST

## Current State: Phase 2 COMPLETE — Dashboard Enhancements Done

All 4 new dashboard pages built, 3 new API route files created, DatabaseClient extended with 8 new methods, navigation updated with "Operations" section. Build compiles clean (18 routes).

## Completed Work

### Session 4 (2026-04-02): Phase 2 — Dashboard Enhancements

**Backend — DatabaseClient extensions (db/client.py):**
- `get_system_log()` — paginated with action/module/date filtering, returns (entries, total)
- `get_error_log()` — filtered for FAIL results, paginated
- `get_queue_items()` — all items with status filter + pagination (not just READY)
- `update_queue_item()` — update any fields by ID (approve/reject/edit)
- `get_queue_stats()` — counts grouped by status
- `update_schedule_config()` — was missing, called by schedule.py route
- `create_feed_source()`, `update_feed_source()`, `delete_feed_source()` — full CRUD

**Backend — New API Routes:**
- `api/routes/queue.py` — GET /api/queue (list+filter), GET /api/queue/stats, PUT /api/queue/{id}, POST /api/queue
- `api/routes/pipeline.py` — POST /api/pipeline/run (trigger), GET /api/pipeline/runs, GET /api/pipeline/runs/{id}, GET /api/pipeline/errors
- `api/routes/feeds.py` — GET/POST/PUT/DELETE /api/feeds
- Registered all 3 new routers in `api/server.py`

**Frontend — New Dashboard Pages:**
- `/queue` — Queue management: status filter tabs with counts, approve/reject/edit actions, create dialog, pagination. Status-driven color coding with live pulse for IN_PROGRESS items.
- `/runs` — Pipeline runs: "Run Now" trigger with dry-run toggle, run history with expandable details, auto-refresh for active runs, action stat pills (posts/comments/replies/phantom).
- `/errors` — Error dashboard: aggregated from pipeline_runs + system_logs, severity indicators (critical/error/warning with pulsing dots), module grouping, expandable error details, All/Pipeline/System tabs.
- `/config/feeds` — Feed management: CRUD with active/inactive toggle, category badges, type selector, last-fetched timestamps, 2-column card grid.

**Frontend — Navigation Update (layout.tsx):**
- Added "Operations" section divider with Queue, Pipeline Runs, Errors
- Added Feeds under Configuration section
- 4 new Lucide icons imported (ListTodo, Play, AlertTriangle, Rss)

**Frontend — API Client (api.ts):**
- Added QueueItem, QueueResponse, QueueStats types + getQueue, getQueueStats, updateQueueItem, createQueueItem
- Added PipelineRun, PipelineRunsResponse, PipelineError, ErrorsResponse types + getPipelineRuns, triggerPipelineRun, getPipelineErrors
- Added FeedSource, FeedsResponse types + getFeeds, createFeed, updateFeed, deleteFeed

**Build verified:** `next build` compiles clean — 18 routes, 0 errors.

### Session 3 (2026-04-02): Phase 0 + Phase 1

**Phase 0 — Fix What Exists (all 5 tasks):**
- Fixed LLM config: Replaced broken Bedrock SDK with OpenAI-compatible client for Anker AI Router (`llm/provider.py`). 4-tier fallback: AI Router → Direct Anthropic → OpenAI → Templates.
- Updated Chrome UA from 124 → 131 in `browser/context_manager.py`
- Verified LinkedIn ARIA selectors still valid (last checked 2026-02-08)
- Verified Google Sheets connection working
- Confirmed dry-run pipeline completes

**Phase 1 — Replace Google Sheets with Postgres (all 6 tasks):**
- 1.1: Added sqlalchemy, asyncpg, psycopg2-binary, alembic to `requirements.txt`
- 1.2: Created `db/models.py` — 13 SQLAlchemy 2.0 models with indexes
- 1.3: Created Alembic infrastructure, ran initial migration (13 tables in local Postgres)
- 1.4: Created `db/client.py` — DatabaseClient mirrors every SheetsClient method. Tested all 12 methods against live DB.
- 1.5: Created `db/seed.py` — imported 662 rows from Google Sheets (180 targets, 178 content bank, 146 reposts, 88 safety terms, 59 rules, 8 feeds, etc.)
- 1.6: Swapped data layer — `api/deps.py`, `main.py`, `scheduler.py`, `scheduling/orchestrator.py`, `api/services/analytics_service.py` all use `DATA_BACKEND=postgres` toggle. All imports verified passing.

### Previous Sessions
- Session 2 (2026-03-04): Dashboard build, CRUD forms, Docker verified
- Session 1 (prior): FastAPI backend, Next.js dashboard, 12 pages

## Key Files Created/Modified

### New Files (Phase 2):
- `api/routes/queue.py` — Queue CRUD API (GET/POST/PUT with status filtering)
- `api/routes/pipeline.py` — Pipeline trigger + run history + error aggregation API
- `api/routes/feeds.py` — Feed source CRUD API
- `dashboard/src/app/queue/page.tsx` — Queue management page (approve/reject/edit, status tabs, stats)
- `dashboard/src/app/runs/page.tsx` — Pipeline runs page (trigger, history, auto-refresh)
- `dashboard/src/app/errors/page.tsx` — Error dashboard (pipeline + system errors, severity, tabs)
- `dashboard/src/app/config/feeds/page.tsx` — Feed management page (CRUD, active toggle, categories)

### Modified Files (Phase 2):
- `db/client.py` — Added 8 new methods (get_system_log, get_error_log, get_queue_items, update_queue_item, get_queue_stats, update_schedule_config, create/update/delete_feed_source)
- `api/server.py` — Registered queue, pipeline, feeds routers
- `dashboard/src/app/layout.tsx` — Added Operations nav section (Queue, Runs, Errors) + Feeds under Config
- `dashboard/src/lib/api.ts` — Added Queue/Pipeline/Feeds/Errors types + API functions

### New Files (Phase 1):
- `db/__init__.py` — module init
- `db/engine.py` — sync + async SQLAlchemy engines, dotenv loading
- `db/models.py` — 13 tables: system_logs, outbound_queue, engine_control, schedule_configs, safety_terms, reply_rules, comment_templates, comment_targets, content_bank, repost_bank, activity_windows, feed_sources, pipeline_runs
- `db/client.py` — DatabaseClient with full SheetsClient API compatibility + TAB_* constants + pipeline_runs + feed_sources methods
- `db/seed.py` — one-time Sheets → Postgres migration tool
- `db/alembic.ini`, `db/alembic/env.py`, `db/alembic/versions/304cd6261f7a_initial_schema_13_tables.py`

### Modified Files:
- `.env` — added DATABASE_URL, DATA_BACKEND, AI_ROUTER_* vars
- `requirements.txt` — added DB dependencies
- `llm/provider.py` — rewritten for Anker AI Router (OpenAI-compatible)
- `browser/context_manager.py` — Chrome UA 131
- `api/deps.py` — DATA_BACKEND toggle, returns DatabaseClient or SheetsClient
- `main.py`, `scheduler.py`, `scheduling/orchestrator.py` — dynamic backend factory
- `api/services/analytics_service.py` — removed SheetsClient type annotation

## Database State
- **Local Postgres**: `postgresql://kylebartlett@localhost:5432/linkedin_machine`
- **13 tables**, all populated via seed script
- **EngineControl**: mode=Live, phase=stealth
- **662 rows** total across all tables

## Next Steps (Phase 3: Pipeline Execution Wiring)

1. **Wire "Run Now" to actual pipeline** — Connect POST `/api/pipeline/run` to actually invoke `main.py` as a subprocess (currently just creates a DB record). Use `asyncio.create_subprocess_exec` in pipeline.py route. File: `api/routes/pipeline.py`
2. **Pipeline status WebSocket** — Add `/api/pipeline/ws` WebSocket endpoint for real-time run status updates (similar to alerts WS). Push status changes as pipeline progresses.
3. **History page fix** — `api/routes/history.py` still calls `sheets.get_system_log()` which doesn't exist on DatabaseClient. Replace with `client.get_system_log()` (now available). Same for analytics_service.py.
4. **Schedule config update fix** — `api/routes/schedule.py` calls `sheets.update_schedule_config()` which didn't exist on DatabaseClient. Now fixed with `client.update_schedule_config()` but route still uses old import pattern.
5. **End-to-end test** — Start FastAPI server + Next.js dashboard, verify all 18 pages load, test CRUD operations on queue/feeds/pipeline.
6. **Pipeline actual execution** — Full dry run: ingest → summarize → generate → (skip LinkedIn posting) → verify logs in system_logs table.

## Architecture Reference
- **Data Layer**: `db/` module (Postgres via SQLAlchemy 2.0). Toggle: `DATA_BACKEND=postgres|sheets`
- **API**: FastAPI at `api/server.py`, deps at `api/deps.py` (returns DatabaseClient)
- **Dashboard**: Next.js 16 at `dashboard/`
- **Pipeline**: `main.py` → orchestrator → commenter/replier/poster (all use data client)
- **LLM**: Anker AI Router (OpenAI-compatible) at `llm/provider.py`
- **Browser**: Playwright with stealth at `browser/`
