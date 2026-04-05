# ENGRAM — AI LinkedIn Machine

> Last updated: 2026-04-04T16:00 CST

## Current State: AUTO-CONNECTION ENGINE WITH VOICE OUTREACH — FULLY BUILT

### Session 14 (2026-04-04): Auto-Connection Engine + ElevenLabs Voice Outreach

**What was built:**

Browser automation (`browser/linkedin_actions.py` — 5 new functions):
- `get_profile_info(page, profile_url)` — Scrape name, headline, about, experience, location, mutual connections
- `send_connection_request(page, profile_url, note)` — 3 strategies to find Connect button, handles "Add a note" flow, 300-char limit
- `search_linkedin_people(page, query, max_results)` — Search LinkedIn People, return list of profile dicts
- `get_new_connections(page, max_results)` — Check My Network for recently accepted connections
- `open_dm_and_send_audio(page, profile_url, audio_path, text)` — Send DM with audio file attachment

Config (`config/connector.yaml`):
- daily_limit: 25, commenter_priority: true
- Search keywords: AI automation, supply chain, operations, demand planning, etc.
- Title keywords: CTO, VP Engineering, Director of Operations, Head of AI, etc.
- Voice config: ElevenLabs eleven_multilingual_v2, stability 0.5, similarity_boost 0.8
- Rate limiting: 45-90s between requests, 120s between searches, 2h voice delay

Core engine (`engagement/connector.py`):
- `run_connector(max_requests, headless, dry_run, commenter_only, outbound_only)` — Main entry
- `_auto_connect_commenters()` — Scan Kyle's posts for commenters, scrape profiles, LLM note, send request
- `_outbound_search_connect()` — Search by keywords, score by title relevance, scrape, LLM note, send
- `_score_candidates()` — Rank search results by title keyword match + mutual connections
- `get_connector_status()` — API helper for dashboard
- Connection tracker JSON at `tracking/linkedin/connections.json`
- CLI: `python engagement/connector.py --commenter-connect --dry-run`

LLM functions (`llm/provider.py` — 2 new functions):
- `generate_connection_note(profile_info, persona_system_prompt, context)` — <=300 char personalized note
- `generate_voice_script(profile_info, persona_system_prompt)` — 75-150 word conversational voice script

Voice outreach (`engagement/voice_outreach.py`):
- `monitor_and_send_voice(headless, dry_run, max_messages)` — Check My Network, generate scripts, TTS, send DM
- `_generate_audio(script, voice_config, output_path)` — ElevenLabs TTS with cloned voice
- `test_voice_generation(text)` — Quick test of ElevenLabs integration
- CLI: `python engagement/voice_outreach.py --dry-run` or `--test`

API routes (`api/routes/connector.py`):
- GET /connector/status — Daily counts, budget, config summary
- GET /connector/requests — Connection request history (filterable by source)
- POST /connector/run — Trigger connector (commenter_only, outbound_only, dry_run)
- GET /connector/acceptances — Pending voice follow-ups
- GET /connector/voice-queue — Voice message queue (pending + sent)
- POST /connector/voice-run — Trigger voice outreach
- GET /connector/config — Full connector config
- PUT /connector/config — Partial config update

Dashboard (`dashboard/src/app/connections/page.tsx`):
- Budget bar showing daily requests sent vs limit
- 4 stat cards: sent today, from commenters, from outbound, all-time total
- Quick action buttons: Connect Commenters, Outbound Search, Send Voice Messages, Dry Run
- Search keyword badges from config
- Tab 1: Connection Requests — filterable by source, expandable rows with note preview, profile links
- Tab 2: Voice Messages — split view with pending follow-ups and sent messages, expandable scripts

Orchestrator wiring (`scheduling/orchestrator.py`):
- Steps 7-8 added: run_connector + monitor_and_send_voice after replying, before phantom heartbeats
- Summary dict expanded with connections_sent and voice_messages counts

Other updates:
- `requirements.txt` — Added `elevenlabs`
- `.env.example` — Added ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
- `api/server.py` — Mounted connector router (17 total route modules)
- `dashboard/src/lib/api.ts` — All connector types and fetch functions
- `dashboard/src/app/layout.tsx` — Added Connections nav item with Link2 icon

**Build verified:** `next build` compiled successfully, 22 pages (was 21).

### Session 13 (2026-04-04): Dashboard Gap Analysis + New Pages

**What was built:**

Backend API routes (3 new):
- `api/routes/heartbeat.py` — GET /heartbeat/status, GET/PUT /heartbeat/schedule/{name}, POST /heartbeat/run/{name}, POST /heartbeat/run-all
- `api/routes/killswitch.py` — GET /kill-switch, POST /kill-switch/activate, POST /kill-switch/deactivate
- `api/routes/leads.py` — GET /leads, PUT /leads/{name}, DELETE /leads/{name}
- All 3 mounted in `api/server.py`

Dashboard API client (`dashboard/src/lib/api.ts`):
- Added: getHeartbeatStatus, getPersonaSchedule, updatePersonaSchedule, triggerHeartbeat, triggerAllHeartbeats
- Added: getKillSwitch, activateKillSwitch, deactivateKillSwitch
- Added: getLeads, updateLead, deleteLead
- Added: getPersonaDetail, getPipelineRun (previously missing)

Dashboard pages (3 new):
- `/personas/scheduler` — Per-persona heartbeat control panel with kill switch, schedule editing, trigger controls, daily stats, session status, active hours. Each persona has color-coded card with status dot, probability bars, stat progress bars.
- `/personas/activity` — Per-persona engagement analytics with 30d/14d/7d toggle, total stats summary, stacked activity bars, recent activity table. Tabs for breakdown vs recent.
- `/leads` — Lead tracker with score badges, status management (new/reviewing/qualified/contacted/dismissed/archived), detail dialog with notes, source link, delete. Filterable by status.
- Navigation updated in `layout.tsx` with new "Personas" section (Scheduler, Activity, Leads)

**Build verified:** `next build` compiled successfully, 21 pages generated (was 18).

**Gap analysis completed:**
- Found 4 Python modules with NO API routes (heartbeat, leads, phantom, kill_switch) — 3 now have routes
- Found 2 backend endpoints not consumed by frontend (persona detail, pipeline run detail) — now have api.ts functions
- `engagement/phantom.py` still CLI-only (no dedicated API route — uses heartbeat system instead)

### Session 12 (2026-04-04): Per-Persona Heartbeat Schedules

**What was built:**
- `scheduling/heartbeat.py` — Per-persona autonomous runner with CLI
- `engagement/tracker.py` — `get_daily_stats(persona=...)` now supports per-persona filtering
- `config/personas.json` — Added `schedule` block to all 6 phantoms + `linkedin_url` for MainUser
- `scheduler.py` — Phantom heartbeat loop runs alongside existing orchestrator

**How it works:**
Each phantom persona runs independently on their own schedule. Every cycle:
1. Checks `active_hours` (timezone-aware) — skips if outside window
2. Checks for active browser session — skips if no saved cookies
3. Comments on feed posts via `run_commenter(persona_name=...)`
4. Randomly comments on Kyle's posts via `run_phantom_on_post()` (30% chance for Marcus)
5. Randomly generates + posts own content via LLM + `post_single()` (15% chance for Marcus)

**Schedule config per persona (in personas.json):**
```json
"schedule": {
  "comments_per_cycle": 2,      // feed comments per heartbeat
  "post_chance_per_cycle": 0.15, // probability of making a post
  "kyle_comment_chance": 0.3,    // probability of commenting on Kyle
  "cycle_interval_minutes": 60   // how often heartbeat runs
}
```

**Dry-run verified:** Marcus Chen detected as only eligible persona (only one with active session), generated comment on Austin Richard's feed post, quality score passed, per-persona daily stats working (1/3 comments used).

**CLI:**
- `venv/bin/python3 scheduling/heartbeat.py --persona "The Visionary Advisor" --dry-run`
- `venv/bin/python3 scheduling/heartbeat.py --all --dry-run`
- `venv/bin/python3 scheduling/heartbeat.py --all` (live)

**Safety:** Only personas with active browser sessions participate. Other 5 phantoms are safely off (no sessions). Kill switch checked between every step.

### Session 11 (2026-04-03): Replier E2E + Phantom Persona Kickoff

**Replier fully tested and live:**
- 5 iterative test/fix cycles to get replier working end-to-end
- Successfully posted 1 live reply to Brian Kerrigan on LinkedIn
- Bugs fixed: LLM proxy model detection, activity page selectors, comment author extraction, self-comment filtering, dry-run tracker isolation, safety filter false positives

**Commenter fix committed:**
- `8cf6fb7` — 404 detection + expanded target pool in commenter

**LLM provider fixes:**
- Proxy auto-detection: when `ANTHROPIC_BASE_URL` contains "ai-router" or "litellm", use `vertex_ai/claude-opus-4-6` model format instead of `claude-opus-4-6-20250610`
- OpenAI GPT-5.2: `max_tokens` → `max_completion_tokens` (API breaking change)

**Safety filter relaxed:**
- `\bconsulting\b` was too broad, changed to `\b(my|our|I offer|offering)\s+consulting\b`

**Phantom persona plan approved but NOT started:**
- Marcus Chen ("The Visionary Advisor") has completed LinkedIn warmup
- Credentials provided: Email `Marcus.Chen26@icloud.com`, Password `Bartdog6969!` (user will change later)
- Session dir: `~/.ai-linkedin-machine/sessions/the_visionary_advisor/`

### Git Commits This Session
- `8cf6fb7` fix: add 404 detection and expand target pool in commenter
- `ed21fc6` fix: LLM proxy model detection, replier activity page support, comment author extraction
- `55914b7` fix: relax consulting safety filter + skip tracker persistence on dry runs

## Next Steps — SPECIFIC (Pick up here)

### Step 1: Clone Kyle's voice in ElevenLabs
- Go to ElevenLabs dashboard → Voice Cloning → upload samples of Kyle speaking
- Get the voice_id and set `ELEVENLABS_VOICE_ID` in `.env`
- Test: `venv/bin/python3 engagement/voice_outreach.py --test`

### Step 2: Dry-run the connector end-to-end
- `venv/bin/python3 engagement/connector.py --commenter-connect --dry-run`
- `venv/bin/python3 engagement/connector.py --outbound --dry-run`
- Verify: profile scraping works, LLM notes are personalized and under 300 chars, safety filter passes

### Step 3: Live test — single connection request
- `venv/bin/python3 engagement/connector.py --commenter-connect --max 1`
- Verify: connection request actually sent on LinkedIn with personalized note

### Step 4: Test voice outreach
- `venv/bin/python3 engagement/voice_outreach.py --dry-run`
- Verify: script generation, ElevenLabs audio output, DM sending flow

### Step 5: Login remaining phantom personas (5 of 6)
- Dr. Priya Nair, Jake Morrison, Rebecca Torres, Alex Kim, David Okafor
- `venv/bin/python3 scripts/login.py "<persona_name>"` for each

### Step 6: Deploy to Coolify (production)
- Docker compose with FastAPI + Next.js + Postgres
- Reverse proxy, SSL, environment variables

## Key Files Modified This Session (Session 14)

| File | Change |
|------|--------|
| `browser/linkedin_actions.py` | 5 new async functions for connection automation (profile scraping, connect, search, DM) |
| `config/connector.yaml` | NEW — Search keywords, title keywords, voice config, rate limiting |
| `engagement/connector.py` | NEW — Auto-connection engine (commenter + outbound search) |
| `engagement/voice_outreach.py` | NEW — ElevenLabs voice follow-up for accepted connections |
| `llm/provider.py` | 2 new functions: generate_connection_note, generate_voice_script |
| `api/routes/connector.py` | NEW — 8 endpoints for connector status, requests, triggers, voice queue, config |
| `api/server.py` | Mounted connector router (17 total route modules) |
| `dashboard/src/app/connections/page.tsx` | NEW — Connections dashboard with budget bar, request list, voice queue |
| `dashboard/src/lib/api.ts` | Connector types and fetch functions |
| `dashboard/src/app/layout.tsx` | Added Connections nav item |
| `scheduling/orchestrator.py` | Steps 7-8: connector + voice outreach wired into orchestration cycle |
| `requirements.txt` | Added elevenlabs |
| `.env.example` | Added ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID |

## Marcus Chen Reference

- **Persona name in code**: `"The Visionary Advisor"`
- **Display name**: `Marcus Chen`
- **Voice**: Confident, forward-looking, high-energy but not hype. 2-4 sentences, punchy.
- **Signature phrases**: "Here's the thing nobody's talking about", "The real unlock isn't..."
- **Engagement rules**: Triggers on AI strategy, startup ops, tech leadership. Debates with Jake Morrison (skeptic vs visionary). Agrees with David Okafor (ROI alignment).
- **System prompt**: Full backstory — 15yr career, 3 exits, fractional CTO, angel investor
- **Config location**: `config/personas.json` (search for "The Visionary Advisor")
- **Session dir**: `~/.ai-linkedin-machine/sessions/the_visionary_advisor/`
- **Browser context**: `PersonaContext("The Visionary Advisor", headless=False)`

## Architecture Reference
- **Data Layer**: `db/` module (Postgres via SQLAlchemy 2.0). Toggle: `DATA_BACKEND=postgres|sheets`
- **API**: FastAPI at `api/server.py`
- **Dashboard**: Next.js 16 at `dashboard/`
- **Pipeline**: `main.py` → orchestrator → commenter/replier/poster
- **LLM**: Claude Opus 4.6 via ai-router proxy at `llm/provider.py`
- **Browser**: Playwright with stealth at `browser/`
- **Personas**: `config/personas.json` (7 total: 1 MainUser + 6 phantoms)
