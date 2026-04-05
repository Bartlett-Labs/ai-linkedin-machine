# PROJECT LOG — AI LinkedIn Machine

> Append-only. Each entry timestamped. Never delete entries.

---

## 2026-04-04T16:00 — Session 14: Auto-Connection Engine + ElevenLabs Voice Outreach

### Auto-Connection Engine
- `engagement/connector.py` — Full auto-connection engine with commenter-first priority + outbound search
- `config/connector.yaml` — Search keywords, title keywords, voice config, rate limiting (45-90s delays)
- `browser/linkedin_actions.py` — 5 new async functions: profile scraping, connection requests, people search, acceptance monitoring, audio DM sending
- Connection tracker at `tracking/linkedin/connections.json` with daily budget management (~25/day on Premium)

### ElevenLabs Voice Outreach
- `engagement/voice_outreach.py` — Monitor acceptances, generate personalized 30-60s voice scripts via LLM, convert to audio via ElevenLabs TTS (Kyle's cloned voice), send as LinkedIn DM
- Configurable 2-hour delay after acceptance before DMing
- CLI: `--test` for ElevenLabs integration test, `--dry-run` for full flow without sending

### LLM Functions
- `generate_connection_note()` — <=300 char personalized connection notes referencing specific profile details
- `generate_voice_script()` — 75-150 word conversational voice scripts for TTS

### Orchestrator Integration
- `scheduling/orchestrator.py` — Steps 7-8 added: connector + voice outreach after replying
- Summary dict expanded with `connections_sent` and `voice_messages`

### API + Dashboard
- `api/routes/connector.py` — 8 endpoints (status, requests, triggers, voice queue, config CRUD)
- `dashboard/src/app/connections/page.tsx` — Budget bar, stat cards, quick actions, request list with expandable notes, voice queue with script preview
- Total: 22 dashboard pages, 17 API route modules
- `next build` clean

---

## 2026-04-04T14:30 — Session 13: Dashboard Expansion — 3 New Pages + Gap Audit

### Gap Analysis
- Audited all 13 FastAPI route modules against dashboard api.ts consumption
- Found 4 Python modules with zero API routes: heartbeat, lead_tracker, phantom, kill_switch
- Found 2 backend endpoints not consumed by frontend: persona detail, pipeline run detail

### New Backend API Routes
- `api/routes/heartbeat.py` — Heartbeat status, per-persona schedule CRUD, trigger runs (single + all)
- `api/routes/killswitch.py` — Kill switch status, activate, deactivate
- `api/routes/leads.py` — Lead listing (filterable), update status/notes, delete
- All mounted in `api/server.py` (16 total route modules now)

### Dashboard API Client Updates
- Added heartbeat, kill switch, leads functions to `dashboard/src/lib/api.ts`
- Added missing functions: getPersonaDetail, getPipelineRun

### New Dashboard Pages
- `/personas/scheduler` — Per-persona heartbeat control with kill switch banner, schedule editing, trigger controls, daily stats, color-coded cards
- `/personas/activity` — Per-persona engagement analytics with time range toggle, activity bars, recent activity table
- `/leads` — Lead tracker with scoring, status management, detail dialog, filtering
- Navigation updated with new "Personas" section in sidebar

### Build
- `next build` compiled successfully, 21 pages (was 18)
- All icon import issues resolved (Heartbeat → HeartPulse, Timer → Clock3)

---

## 2026-04-03T21:30 — Session 11: Replier E2E + Phantom Persona Kickoff

### Replier Testing & Fixes
- Tested replier end-to-end across 5 iterative runs
- Fixed LLM proxy model detection: `ANTHROPIC_BASE_URL` with "ai-router" auto-selects `vertex_ai/claude-opus-4-6`
- Fixed OpenAI param: `max_tokens` → `max_completion_tokens` for GPT-5.2
- Fixed activity page comment extraction: fallback to `div[data-urn]` selectors
- Fixed comment author extraction: profile link text empty on activity pages, added text-based fallback
- Fixed self-comment filtering: replier was trying to reply to Kyle's own comments
- Fixed dry-run isolation: tracker persistence and daily stats now skipped during dry runs
- Fixed safety filter: `\bconsulting\b` too broad, changed to `\b(my|our|I offer|offering)\s+consulting\b`
- Cleaned tracking file: removed 4 dry-run reply entries from `tracking/linkedin/2026-04-03.md`
- **Live result**: Successfully posted 1 reply to Brian Kerrigan

### Commenter Fix
- Added 404 detection to `engagement/commenter.py`
- Expanded target pool to reduce failures

### Commits
- `8cf6fb7` fix: add 404 detection and expand target pool in commenter
- `ed21fc6` fix: LLM proxy model detection, replier activity page support, comment author extraction
- `55914b7` fix: relax consulting safety filter + skip tracker persistence on dry runs

### Phantom Persona System Started
- User requested Marcus Chen ("The Visionary Advisor") implementation — first phantom to go live
- Marcus has completed LinkedIn warmup phase
- Credentials received (email + password for manual login)
- Plan created and approved: init_session.py → manual login → phantom.py → test → verify
- Tasks #28-31 created but implementation NOT started (session ending)

---

## 2026-04-03T11:00 — Session 10: RSS Ingestion Fix + Pipeline Dry Run

- RSS ingest rewritten with hash manifest dedup + 7-day recency filter
- Hash manifest seeded with 4,204 hashes
- Queue cleaned: 2,078 re-ingested articles archived, 27 stale summaries archived
- Dry run verified: 8 feeds in ~7s, full pipeline ~100s

---

## 2026-04-02 — Sessions 7-9: Webhook, Pipeline Streaming, Dashboard

- Session 9: Real-time WebSocket pipeline streaming, usePipelineStatus hook, live terminal console
- Session 8: Pipeline execution wiring, data layer consistency, 8 E2E bugs fixed
- Session 7: LinkedIn webhook go-live (webhooks.bartlettlabs.io), challenge-response validated

---

## 2026-04-02 — Sessions 3-6: Foundation Build

- Session 6: LinkedIn webhook service (FastAPI on port 3847, auto-queues replies)
- Session 5: Security audit (SSRF, timing-safe auth, input validation, CORS)
- Session 4: Phase 2 dashboard (queue, pipeline runs, errors, feeds pages)
- Session 3: Phase 0 fixes + Phase 1 Postgres migration (13 tables, 662 rows seeded)

---

## 2026-03-04 — Session 2: Dashboard Build

- Dashboard CRUD forms, Docker verified

---

## Prior — Session 1: Initial Build

- FastAPI backend, Next.js dashboard, 12 pages, original pipeline code
