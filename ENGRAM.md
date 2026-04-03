# ENGRAM — AI LinkedIn Machine

> Last updated: 2026-04-02T20:15 CST

## Current State: Phase 2 COMPLETE + Webhook VALIDATED BY LINKEDIN + API Keys APPROVED

All Phase 2 work complete. LinkedIn webhook microservice built, deployed, and **validated by LinkedIn** — challenge-response confirmed live via `webhooks.bartlettlabs.io`. LinkedIn API keys also approved (2026-04-02). 14 tables in Postgres, 18 dashboard routes.

### Session 7 (2026-04-02): Webhook Go-Live
- Stopped PM2-managed `bartlett-webhooks` Node.js service that was occupying port 3847 (`pm2 stop bartlett-webhooks`)
- Started LinkedIn webhook FastAPI service on port 3847 (PID-based, not PM2)
- Verified cloudflared tunnel running (PID 2077) — `webhooks.bartlettlabs.io → localhost:3847`
- Health check confirmed: `{"status":"ok","service":"linkedin-webhook"}`
- **LinkedIn validated the webhook** — challenge-response passed, endpoint registered in Developer Portal
- **LinkedIn API keys approved** — full programmatic access granted

### Pending
- Update `LINKEDIN_ACCESS_TOKEN` in `.env` (currently placeholder)
- Update `LINKEDIN_ORG_URN` in `.env` (currently `REPLACE_WITH_ORG_ID`)
- Consider replacing PM2 `bartlett-webhooks` with LinkedIn webhook service permanently (`pm2 delete bartlett-webhooks`)

## Completed Work

### Session 6 (2026-04-02): LinkedIn Webhook Service

**Architecture**: Separate FastAPI microservice on port 3847, behind Cloudflare tunnel (`webhooks.bartlettlabs.io → localhost:3847`). Shares `db/` module with main API.

**New DB model — `WebhookEvent` (table 14, `db/models.py`):**
- Fields: id, received_at, event_type, action, notification_id (unique), organization_urn, source_post_urn, generated_activity_urn, actor_urn, comment_text, raw_payload (JSONB), processed, queue_item_id
- Indexes on: received_at, action, notification_id, processed

**Alembic migration**: `a7b2c9d3e4f1_add_webhook_events_table.py` — ran successfully against local Postgres.

**DatabaseClient extensions (`db/client.py`) — 4 new methods:**
- `create_webhook_event(event_data)` — insert event, return ID
- `get_webhook_event_by_notification_id(notification_id)` — dedup lookup
- `get_webhook_events(limit, offset, action_filter, processed)` — list with filtering, returns (events, total)
- `update_webhook_event_queue_link(event_id, queue_item_id)` — link event to auto-queued reply

**Webhook service (`webhook/server.py`):**
- `GET /` — LinkedIn challenge-response validation (HMAC-SHA256 of challengeCode with client secret)
- `POST /` — Receive batched social action notifications. Deduplicates by notification_id. Stores all events. Auto-queues reply drafts for COMMENT actions. Logs to system_logs audit trail.
- `GET /health` — service health check
- Returns 200 within 3 seconds (LinkedIn requirement)

**Environment & infrastructure:**
- `.env` — added `LINKEDIN_ORG_URN`, `WEBHOOK_PORT=3847` (client secret already existed)
- `start.sh` — process manager script: `./start.sh` (both), `./start.sh api`, `./start.sh webhook`, `./start.sh stop`

**E2E test results (all 5 passed):**
1. Health check — `{"status":"ok","service":"linkedin-webhook"}`
2. Challenge validation — HMAC-SHA256 response generated correctly
3. COMMENT ingestion — event stored, reply auto-queued to outbound_queue (status=READY)
4. Deduplication — same notificationId rejected (duplicates=1, created=0)
5. LIKE action — event stored, no auto-queue (queued=0)

**DB verification:** webhook_events populated, outbound_queue has auto-queued reply with notes linking to webhook event, system_logs has audit entries with module=webhook.

### Session 5 (2026-04-02): Fullstack Guardian Security Audit

**Audit scope**: All Phase 2 code — 3 API route files, 4 frontend pages, deps layer, server config.

**CRITICAL fixes:**
- `deps.py` — Replaced timing-unsafe `!=` with `hmac.compare_digest()` for API key comparison. Added security logging for auth failures.
- `pipeline.py` — Added active run concurrency guard on `POST /api/pipeline/run` — rejects with 409 if a run is already running/pending. Prevents DoS via unlimited pipeline triggers.
- `feeds.py` — Added SSRF protection: `_validate_feed_url()` rejects URLs pointing to localhost, private IPs (127.x, 10.x, 172.16-31.x, 192.168.x, 169.254.x), and non-HTTP schemes.

**HIGH fixes:**
- `queue.py` — Added `Literal` type validation for status (5 valid values), persona (7 valid values), and action_type (4 valid values). Invalid enum values now rejected with 422.
- `queue.py`, `pipeline.py` — Bounded `limit` (1-500) and `offset` (>=0) with `Query(ge=, le=)` on all paginated GET endpoints.
- `queue.py`, `pipeline.py`, `feeds.py` — Replaced `{"status": "not_found"}` with 200 → proper `HTTPException(404)` for not-found responses.

**MEDIUM fixes:**
- `server.py` — Tightened CORS from `allow_methods=["*"], allow_headers=["*"]` → explicit whitelist `["GET","POST","PUT","DELETE","OPTIONS"]` and `["Content-Type","X-Api-Key","Authorization"]`.
- `feeds.py` — Added `Field(min_length=1, max_length=200)` on name, `Field(max_length=2000)` on URL. Added `Literal` types for feed type (rss/atom/json/scraper) and category (6 valid values + empty).
- `queue.py` — Added `Field(max_length=10000)` on draft_text, `Field(max_length=2000)` on notes/target_url.
- `feeds/page.tsx` — Added `AlertDialog` delete confirmation before removing feed sources. Installed `shadcn alert-dialog` component.

**Security logging added** to all mutation endpoints (create/update/delete) across queue.py, pipeline.py, feeds.py.

**Build verified:** `next build` compiles clean — 18 routes, 0 errors.

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

### New Files (Webhook Service):
- `webhook/__init__.py` — module init
- `webhook/server.py` — FastAPI webhook service (GET challenge-response, POST notification ingestion, health check)
- `db/alembic/versions/a7b2c9d3e4f1_add_webhook_events_table.py` — migration for table 14
- `start.sh` — process manager script (api/webhook/stop/all)

### Modified Files (Webhook Service):
- `db/models.py` — Added `WebhookEvent` model (table 14) with notification_id unique constraint
- `db/client.py` — Added 4 webhook methods (create_webhook_event, get_webhook_event_by_notification_id, get_webhook_events, update_webhook_event_queue_link)
- `.env` — Added `LINKEDIN_ORG_URN`, `WEBHOOK_PORT=3847`

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
- **14 tables** (13 original + webhook_events), all populated via seed script
- **EngineControl**: mode=Live, phase=stealth
- **662 rows** total across original tables

## Webhook Service
- **Endpoint**: `webhooks.bartlettlabs.io` → Cloudflare tunnel → `localhost:3847`
- **LinkedIn Client ID**: `863cehzc8gq3eb` (Bartlett Labs)
- **Challenge validation**: HMAC-SHA256 of challengeCode with LINKEDIN_CLIENT_SECRET
- **Auto-queue**: COMMENT actions create outbound_queue entries (status=READY, type=reply)
- **Deduplication**: notification_id unique constraint prevents duplicate processing
- **Note**: Port 3847 currently occupied by existing Node.js service — stop that before starting webhook service, or update Cloudflare tunnel to point to webhook service

## Next Steps

### Immediate: LinkedIn Webhook Registration
1. **Find Bartlett Labs org ID** — needed for `LINKEDIN_ORG_URN` in `.env` (currently placeholder)
2. **Stop existing service on :3847** — `kill $(lsof -ti:3847)` then start webhook: `./start.sh webhook`
3. **Register webhook URL** in LinkedIn Developer Portal — enter `https://webhooks.bartlettlabs.io` with cloudflared tunnel running
4. **Verify validation passes** — LinkedIn will GET the URL with a challengeCode

### Phase 3: Pipeline Execution Wiring
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
