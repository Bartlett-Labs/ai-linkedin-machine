# CLAUDE.md — Project Context for AI Assistants

This file exists to catch any new Claude (or other AI assistant) session up on what this project is, what has been built, and where things stand.

---

## What Is This Project

AI LinkedIn Machine is a Python-based LinkedIn brand-building automation tool for Kyle Bartlett (Bartlett Labs). It has three layers:

1. **Google Sheet ("LinkedIn Stealth Engine")** — The intelligence layer. Contains 10 tabs: ContentBank, RepostBank, CommentTargets, CommentTemplates, ReplyRules, SafetyTerms, ScheduleControl, EngineControl, OutboundQueue, SystemLog. The Sheet queues post drafts (status READY), stores comment targets and templates, holds safety terms, and logs every action. The Sheet is the brain — all strategy changes happen there, not in code.

2. **Python execution engine (this repo)** — Reads from the Sheet, executes actions on LinkedIn via Playwright browser automation, and writes results back. Also handles RSS ingestion, article summarization, and post generation via LLM.

3. **Playwright browser automation** — Each of 7 personas gets a persistent browser context at `~/.ai-linkedin-machine/sessions/{persona_name}/` with saved cookies. Human-like typing simulation. Challenge/CAPTCHA detection with automatic kill switch.

---

## Critical Safety Context

**Kyle is a Demand Planner at Anker.** A previous offer for "AI Automation Manager" was rescinded by Anker. This means:

- NEVER generate content that claims the title "AI Automation Manager", "Automation Lead", "Head of Automation", or any title Kyle doesn't hold
- NEVER mention Anker by name or reference internal systems, SKUs, promotions, or confidential processes
- NEVER signal job searching: "open to work", "looking for opportunities", "interviewing", "job hunt"
- NEVER solicit business: "hire me", "consulting", "freelance", "book a call"
- NEVER use engagement bait: "Agree?", "Repost if you", "Like if you"
- NEVER start comments with generic praise: "Great post!", "Love this!", "So insightful!"

Safety is enforced in three places:
1. `SAFETY_PREAMBLE` in `llm/provider.py` — injected into every LLM system prompt before generation
2. `summarization/safety_filter.py` — post-generation check against 30+ blocked phrases, plus dynamic terms from the Sheet's SafetyTerms tab
3. `engagement/quality_checker.py` — 8-dimension quality validation scoring 0-100

**If you are modifying any content generation code, you must preserve all three safety layers.**

---

## LLM Configuration

- **Primary:** Claude Opus 4.6 (`claude-opus-4-6-20250610`) via Anthropic API
- **Fallback:** GPT-5.2 via OpenAI API (only used if Anthropic is unavailable)
- **Last resort:** Template strings from the Sheet's CommentTemplates tab

All LLM calls go through `llm/provider.py`. Do not call Anthropic or OpenAI APIs directly from other modules. The provider handles the fallback chain and safety preamble injection.

---

## Personas

Defined in `config/personas.json`. 7 personas total:

| Name | Role | Engagement Style |
|------|------|-----------------|
| **MainUser** | Demand Planner / AI practitioner | Posts content, comments on targets (7-12/day), replies to engagement |
| The Visionary Advisor | Startup advisor | Big-picture strategic takes, forward-looking |
| The Deep Learner | AI researcher | Academic, technical depth, cautious about ethics |
| The Skeptical Senior Dev | Pragmatic engineer | Contrarian, anti-hype, focused on technical debt |
| The Corporate Compliance Officer | Legal/risk | Formal, risk-averse, GDPR/privacy focused |
| The Creative Tinkerer | Hobbyist dev | Enthusiastic, informal, DIY workarounds |
| The ROI-Driven Manager | Operations manager | Bottom-line focused, cost/time efficiency |

Phantom personas (all except MainUser) engage on MainUser's posts after a randomized 2-15 minute delay to boost reach during the golden hour.

---

## Project Structure and Key Files

```
ai-linkedin-machine/
├── llm/provider.py              # LLM abstraction. Claude primary, OpenAI fallback, template fallback.
│                                  Contains SAFETY_PREAMBLE. All content generation routes through here.
│
├── browser/
│   ├── context_manager.py       # PersonaContext: persistent Playwright browser context per persona.
│   │                              ContextPool manages multiple personas. Stealth JS injection.
│   ├── human_typing.py          # human_type_into_contenteditable(): 50-150ms/char delays,
│   │                              QWERTY-based typos, corrections, thinking pauses.
│   └── linkedin_actions.py      # Centralized LinkedIn DOM selectors (SEL dict). Functions:
│                                  navigate_to_feed(), create_post(), comment_on_post(),
│                                  like_post(), get_feed_posts(), get_post_comments().
│                                  LinkedInChallengeDetected exception. check_for_challenge()
│                                  detects CAPTCHAs/verification. create_post() has retry_async.
│
├── sheets/
│   ├── client.py                # SheetsClient: Google Sheets API. Methods for all 10 tabs.
│   │                              get_ready_items(), update_queue_status(), get_comment_targets(),
│   │                              get_safety_terms(), get_engine_control(), log() -> SystemLog.
│   └── models.py                # Dataclasses: QueueItem, CommentTarget, CommentTemplate,
│                                  ReplyRule, SafetyTerm, ScheduleWindow, EngineControl.
│                                  Enums: QueueStatus, Phase, EngineMode, ReplyAction.
│
├── scheduling/
│   ├── orchestrator.py          # run_orchestrator(): Main coordinator. One full cycle:
│   │                              1. Check kill switch
│   │                              2. Load safety terms from Sheet
│   │                              3. Deduplicate post queue
│   │                              4. Read EngineControl (phase, mode)
│   │                              5. Execute MainUser posts from OutboundQueue
│   │                              6. Phantom persona engagement (randomized delay)
│   │                              7. MainUser commenting on targets
│   │                              8. Reply checking on own posts
│   │                              Kill switch checked between each major step.
│   │                              LinkedInChallengeDetected activates kill switch automatically.
│   └── content_calendar.py      # get_weekly_plan(), is_in_posting_window(), get_next_posting_time().
│                                  Content streams: ai_automation 35%, ops_efficiency 25%,
│                                  personal_growth 20%, builder_stories 20%.
│
├── engagement/
│   ├── commenter.py             # run_commenter(): Pulls targets from Sheet or local config.
│   │                              Navigates to target profiles, finds recent posts, generates
│   │                              comments via llm.provider.generate_comment(), validates via
│   │                              quality_checker, posts via Playwright. Interleaved browsing:
│   │                              every 3rd action comes from feed instead of target visit.
│   │                              Kill switch checked in loop.
│   ├── replier.py               # run_replier(): Navigates to MainUser's recent posts, finds
│   │                              new comments, checks ReplyRules from Sheet (BLOCK/REPLY triggers),
│   │                              generates replies via llm.provider.generate_reply().
│   │                              Tracks replied-to comments in queue/engagement/reply_tracker.json.
│   ├── quality_checker.py       # check_quality(): 8-dimension validation:
│   │                              AI tells, engagement bait, self-promotion, length, specificity,
│   │                              flattery, structure variety, authentic voice. Scores 0-100.
│   │                              Returns QualityResult(passed, score, violations, suggestions).
│   │                              Threshold: 60. One retry with feedback if first attempt fails.
│   ├── tracker.py               # Local daily markdown tracking (SECONDARY to Sheet SystemLog).
│   │                              tracking/linkedin/YYYY-MM-DD.md. Functions: log_comment(),
│   │                              log_post(), log_reply(), log_like(), get_daily_stats().
│   └── lead_tracker.py          # Lead identification by title keywords + interest signals.
│                                  JSON storage at tracking/linkedin/leads.json.
│
├── summarization/
│   ├── safety_filter.py         # violates_safety(): 30+ blocked phrases. load_sheet_terms()
│   │                              pulls additional terms from Sheet SafetyTerms tab.
│   │                              get_violations() returns list of matched phrases (for debugging).
│   ├── summarize.py             # run_all(): Reads articles from queue/incoming_raw/, summarizes
│   │                              via llm.provider, checks safety, writes to queue/summaries/.
│   └── prompt_templates/
│       ├── default.txt          # Article summarization prompt
│       ├── employer_neutral.txt # Safety rewrite prompt
│       └── safe_tone.txt        # Tone checking prompt
│
├── posting/poster.py            # run_poster(): Reads posts from queue/posts/, executes via
│                                  Playwright PersonaContext, moves files to done/ or failed/.
│
├── posting_generator/
│   └── generate_post.py         # run_all(): Reads summaries, generates LinkedIn posts via
│                                  llm.provider, runs safety check before saving to queue/posts/.
│
├── ingestion/
│   ├── rss_ingest.py            # ingest(): Reads feeds from config/feeds.json, fetches articles,
│   │                              saves to queue/incoming_raw/.
│   ├── arxiv_ingest.py          # ArXiv paper fetching
│   ├── web_scraper.py           # General article scraping
│   └── youtube_ingest.py        # YouTube transcript extraction
│
├── utils/
│   ├── kill_switch.py           # check_kill_switch(): Returns True if STOP file exists in project root.
│   │                              activate_kill_switch(): Creates STOP file (called on LinkedIn challenges).
│   │                              deactivate_kill_switch(): Removes STOP file.
│   ├── retry.py                 # retry_async(): Exponential backoff with jitter.
│   │                              @with_retry decorator. max_retries=3, base_delay=2.0.
│   └── dedup.py                 # is_duplicate(): Jaccard token similarity, 55% threshold.
│                                  deduplicate_queue(): Removes duplicates from queue/posts/.
│
├── config/
│   ├── personas.json            # 7 persona definitions with system prompts, session dirs, behavior
│   ├── rate_limits.yaml         # Phase-based limits: stealth/announcement/authority
│   ├── feeds.json               # RSS feed URLs
│   └── app_config.yaml          # Core settings: timezone (US/Central), paths, LLM config
│
├── main.py                      # Entry point. Async pipeline with argparse:
│                                  --dry-run, --skip-ingest, --skip-generate,
│                                  --comments-only, --replies-only, --no-headless
│
├── scheduler.py                 # Thin wrapper that runs orchestrator within posting windows
│
├── requirements.txt             # anthropic, openai, playwright, google-api-python-client, etc.
├── .env.example                 # Required env vars documented
└── .gitignore                   # Excludes credentials, sessions, logs, tracking data, queue data
```

---

## Phases and Rate Limits

Defined in `config/rate_limits.yaml`. Current phase is read from Sheet EngineControl tab.

| Phase | Posts | Comments/Day | Phantom Comments/Post | Min Delay |
|-------|-------|-------------|----------------------|-----------|
| stealth | 2/week | 10 | 2 | 300s |
| announcement | 2/day | 15 | 4 | 180s |
| authority | 2/day | 12 | 6 | 120s |

---

## Google Sheet Tabs

| Tab | Purpose | Read/Write |
|-----|---------|------------|
| OutboundQueue | Post drafts with status (READY/DONE/FAILED/SKIPPED) | Read + Write |
| EngineControl | Phase, mode (LIVE/DRY_RUN/PAUSED), feature toggles | Read |
| CommentTargets | LinkedIn profiles to comment on (URL, category, priority) | Read |
| CommentTemplates | Fallback comment templates by style | Read |
| ReplyRules | Triggers for auto-reply (keyword matching, BLOCK/REPLY actions) | Read |
| SafetyTerms | Dynamic blocked phrases (additions don't require code changes) | Read |
| ScheduleControl | Posting windows (day, start time, end time) | Read |
| SystemLog | Every action logged: timestamp, action type, persona, status, details | Write |
| ContentBank | Source content library | Read |
| RepostBank | Repost candidates | Read |

---

## Data Flow

```
1. RSS feeds → ingestion/rss_ingest.py → queue/incoming_raw/
2. queue/incoming_raw/ → summarization/summarize.py → queue/summaries/
3. queue/summaries/ → posting_generator/generate_post.py → queue/posts/
4. queue/posts/ + Sheet OutboundQueue → scheduling/orchestrator.py
5. orchestrator → browser/linkedin_actions.py → LinkedIn
6. orchestrator → sheets/client.py → Sheet SystemLog
```

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | Yes | Claude Opus 4.6 (primary LLM) |
| `GOOGLE_SHEET_ID` | Yes | Sheet ID from URL |
| `GOOGLE_CREDENTIALS_PATH` | Yes | Path to service account JSON |
| `OPENAI_API_KEY` | No | GPT-5.2 fallback |
| `CLAUDE_MODEL` | No | Override default model (default: `claude-opus-4-6-20250610`) |
| `OPENAI_MODEL` | No | Override fallback model (default: `gpt-5.2`) |
| `LINKEDIN_CLIENT_ID` | No | LinkedIn API (for API-based posting) |
| `LINKEDIN_CLIENT_SECRET` | No | LinkedIn API |
| `LINKEDIN_ACCESS_TOKEN` | No | LinkedIn API |
| `HEADLESS` | No | `true`/`false` (default: `true`) |
| `SESSION_DIR` | No | Browser session storage (default: `~/.ai-linkedin-machine/sessions`) |

---

## What Has Been Built (Completed Work)

### Original Build (Steps 1-7)
- Migrated from Selenium to async Playwright with persistent browser contexts
- Built Google Sheets integration (SheetsClient) connecting to all 10 tabs
- Populated all empty config files (rate_limits.yaml, app_config.yaml, personas.json)
- Rewrote commenter.py (full Playwright + Sheet + quality checks)
- Rewrote replier.py from skeleton (Playwright + Sheet + ReplyRules)
- Created quality_checker.py (8-dimension comment validation)
- Created tracker.py (daily markdown activity logs)
- Created lead_tracker.py (lead identification)
- Created orchestrator.py (coordinated multi-persona scheduling)
- Created content_calendar.py (weekly planning + posting windows)
- Rewrote main.py to async pipeline with argparse
- Rewrote scheduler.py as thin orchestrator wrapper
- Created all shell scripts (init.sh, run_ingest.sh, run_poster.sh)
- Populated prompt templates
- Updated .gitignore, created .env.example

### Improvement Pass (Tasks 9-12)
- **Task 9:** Created `llm/provider.py` — LLM abstraction with Claude primary, OpenAI fallback, template last resort. Safety preamble injected into every system prompt pre-generation.
- **Task 10:** Updated all LLM consumers (commenter, replier, summarize, generate_post) to use `llm.provider` instead of calling OpenAI directly.
- **Task 11:** Added LinkedIn challenge/CAPTCHA detection in `linkedin_actions.py`. Added retry with exponential backoff (`utils/retry.py`). Added interleaved browsing pattern in commenter (every 3rd action from feed).
- **Task 12:** Created `utils/kill_switch.py` (local STOP file emergency halt, auto-activates on challenges). Created `utils/dedup.py` (Jaccard similarity content dedup). Added `anthropic` to requirements.txt. Updated .env.example with Anthropic vars. Marked Sheet SystemLog as source of truth (local tracker is secondary).

### Model Updates
- Primary LLM changed from OpenAI to Claude Opus 4.6 (`claude-opus-4-6-20250610`)
- Fallback LLM updated to GPT-5.2

---

## What Has NOT Been Tested Yet

The code has been written but not executed. The following need to be verified:

1. Google Sheet connectivity (service account auth, reading/writing all tabs)
2. Playwright browser launch + persistent session persistence
3. LinkedIn DOM selectors (LinkedIn changes their HTML frequently)
4. LLM API calls (Anthropic + OpenAI key validation)
5. End-to-end: Sheet queue item → Playwright post → Sheet status update
6. Phantom persona engagement timing
7. Safety filter coverage (all blocked phrases caught)
8. Kill switch activation/deactivation
9. The `STOP` file path resolution (relative to project root)
10. RSS ingestion still working after all the refactoring

---

## Separate Project: auto-commenter-platform

There is a separate project at `/Users/kylebartlett/Personal/Bartlett_Labs/Apps/auto-commenter/` — this is a commercial multi-tenant SaaS product (TypeScript/Next.js/Electron). It is a completely different codebase and should NOT be merged with this project. Useful engagement patterns (personalization quality, tracking, lead identification) have already been ported from it into the Python codebase.

---

## Conventions

- All async code uses `asyncio` with `async/await`
- Browser automation uses Playwright (never Selenium)
- All LLM calls go through `llm/provider.py` (never direct API calls)
- Safety is checked both pre-generation (system prompt) and post-generation (safety_filter)
- The Google Sheet is the source of truth; local files are secondary
- Logging uses Python's `logging` module, not print statements
- Config is in YAML/JSON files under `config/`, not hardcoded
- Env vars are loaded from `.env` via `python-dotenv`
