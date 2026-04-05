# CLAUDE.md — Project Context for AI Assistants

This file exists to catch any new Claude (or other AI assistant) session up on what this project is, what has been built, and where things stand.

## Approach
- Think before acting. Read existing files before writing code.
- Be concise in output but thorough in reasoning.
- Prefer editing over rewriting whole files.
- Do not re-read files you have already read unless the file may have changed.
- Test your code before declaring done.
- No sycophantic openers or closing fluff.
- Keep solutions simple and direct.
- User instructions always override this file.

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

- **Primary:** Claude Opus 4.6 via AWS Bedrock (`us.anthropic.claude-opus-4-6-20250610-v1:0`)
- **Also supports:** Direct Anthropic API (`claude-opus-4-6-20250610`) if Bedrock isn't available
- **Fallback:** GPT-5.2 via OpenAI API (only used if Anthropic/Bedrock is unavailable)
- **Last resort:** Template strings from the Sheet's CommentTemplates tab

The provider auto-detects auth method in priority order:
1. **Bedrock proxy** — If `ANTHROPIC_BEDROCK_BASE_URL` + `ANTHROPIC_AUTH_TOKEN` are set, uses a standard `Anthropic` client pointed at the proxy URL with the auth token. This is the current production setup (Anker's ai-router gateway). Model IDs use `global.` prefix.
2. **Standard AWS Bedrock** — If `AWS_REGION` is set, uses `AnthropicBedrock` with standard boto3 credential chain. Model IDs use `us.` prefix.
3. **Direct Anthropic API** — If `ANTHROPIC_API_KEY` is set, uses standard `Anthropic` client. Model IDs use bare format.

All LLM calls go through `llm/provider.py`. Do not call Anthropic or OpenAI APIs directly from other modules. The provider handles the fallback chain and safety preamble injection.

---

## Personas

Defined in `config/personas.json`. 7 personas total. Each phantom persona has: `display_name`, `linkedin_url`, `location`, `active_hours` (timezone-aware), `voice` object (tone, vocabulary, signature_phrases, comment_length, avoids), `engagement_rules` (triggers, debates_with, agrees_with), and an enhanced `system_prompt` encoding full backstory and voice rules.

| Name | LinkedIn Name | Location | Role | Voice |
|------|--------------|----------|------|-------|
| **MainUser** | Kyle Bartlett | — | Demand Planner / AI practitioner | Direct, technical, practical |
| The Visionary Advisor | **Marcus Chen** | Austin, TX | Fractional CTO, startup advisor | Strategic, forward-looking, punchy |
| The Deep Learner | **Dr. Priya Nair** | Boston, MA | AI research scientist (PhD) | Academic, precise, questioning |
| The Skeptical Senior Dev | **Jake Morrison** | Denver, CO | Staff engineer, 16yr production exp | Terse, contrarian, dry humor |
| The Corporate Compliance Officer | **Rebecca Torres, CIPP/US** | Chicago, IL | Dir. AI Governance, Fortune 500 | Formal, risk-aware, structured |
| The Creative Tinkerer | **Alex Kim** | Portland, OR | Indie dev, self-taught maker | Casual, enthusiastic, anecdotal |
| The ROI-Driven Manager | **David Okafor** | Dallas, TX | Dir. Operations, manufacturing | ROI-focused, no-nonsense |

Phantom personas (all except MainUser) engage on MainUser's posts after a randomized 2-15 minute delay to boost reach during the golden hour. They create conversation threads with natural-looking debate (e.g., Marcus vs. Jake on practicality, Priya asking research questions, David demanding ROI numbers).

**Key persona docs:**
- `config/personas.json` — machine-readable definitions with system prompts, voice rules, engagement triggers
- `docs/PERSONA_DOSSIERS.md` — full LinkedIn profile builds (headlines, About sections, experience, skills, setup checklist)
- `docs/PHANTOM_SYSTEM_GUIDE.md` — human-readable usage guide with interaction matrix, setup instructions, safety rules

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
│   ├── client.py                # SheetsClient: Google Sheets API. Methods for all 11 tabs.
│   │                              get_ready_items(), update_queue_status(), get_comment_targets(),
│   │                              get_comment_templates(), get_reply_rules(), get_safety_terms(),
│   │                              get_schedule_configs(), get_schedule_for_phase(),
│   │                              get_engine_control(), get_content_bank(), get_repost_bank(),
│   │                              log() -> SystemLog. ScheduleControl overrides rate_limits.yaml.
│   └── models.py                # Dataclasses: QueueItem, CommentTarget, CommentTemplate,
│                                  ReplyRule, SafetyTerm, ScheduleConfig, EngineControl,
│                                  SystemLogEntry, ContentBankItem, RepostBankItem.
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
├── docs/
│   ├── PERSONA_DOSSIERS.md      # Full LinkedIn profile builds for all 6 phantom personas
│   └── PHANTOM_SYSTEM_GUIDE.md  # Human-readable usage guide for phantom engagement system
│
├── config/
│   ├── personas.json            # 7 persona definitions with system prompts, voice, engagement rules,
│   │                              active_hours, locations. Rich data for phantom personas.
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

| Tab | Columns | Purpose | Read/Write |
|-----|---------|---------|------------|
| SystemLog | Timestamp, Module, Action, Target, Result, Safety, Notes | Every action logged with module derivation and safety status | Write |
| OutboundQueue | Timestamp, ActionType, TargetName, TargetURL, DraftText, Status, Notes, ExecuteLink, CopyReady | Post/comment drafts with status (READY/DONE/FAILED/SKIPPED) | Read + Write |
| EngineControl | Key-value pairs: Mode, Phase, MainUserPosting, PhantomEngagement, Commenting, Replying, LastRun | Phase, mode (LIVE/DryRun/Paused), feature toggles | Read + Write |
| Credentials | Client ID, Client Secret | LinkedIn API credentials (reference only, code uses .env) | Not read |
| ScheduleControl | Mode, PostsPerWeek, CommentsPerDay, PhantomComments | Per-phase rate limits. Overrides config/rate_limits.yaml | Read |
| SafetyTerms | Term, Response | Dynamic blocked phrases (Response: BLOCK or MASK) | Read |
| ReplyRules | ConditionType, Trigger, Action, Notes | Keyword triggers for auto-reply (BLOCK/REPLY/IGNORE) | Read |
| CommentTemplates | ID, TemplateText, Tone, Category, SafetyFlag, ExampleUse, **Persona** | Fallback comment templates by tone/category. 102 MainUser + 90 persona-specific (15 per phantom). Persona column filters by persona name. | Read |
| CommentTargets | ID, Name, LinkedInURL, Category, Priority, LastCommentDate, Notes | LinkedIn profiles to comment on | Read |
| RepostBank | ID, SourceName, SourceURL, Summary, CommentaryPrompt, SafetyFlag, LastUsed, Notes | Repost candidates with commentary prompts | Read |
| ContentBank | ID, Category, PostType, Draft, SafetyFlag, Ready, LastUsed, Notes | Source content library with ready status. Categories: ai_automation, ops_efficiency, personal_growth, builder_stories, **phantom_engagement** (29 multi-persona conversation threads) | Read |

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
| `ANTHROPIC_BEDROCK_BASE_URL` | Yes* | Bedrock proxy URL (e.g. `https://ai-router.anker-in.com/bedrock`). *Required for proxy auth |
| `ANTHROPIC_AUTH_TOKEN` | Yes* | Auth token for Bedrock proxy. *Required for proxy auth |
| `AWS_REGION` | No | AWS region for standard Bedrock (alternative to proxy) |
| `AWS_ACCESS_KEY_ID` | No | AWS credentials for standard Bedrock |
| `AWS_SECRET_ACCESS_KEY` | No | AWS credentials for standard Bedrock |
| `ANTHROPIC_API_KEY` | No | Direct Anthropic API key (alternative to any Bedrock) |
| `GOOGLE_SHEET_ID` | Yes | Sheet ID from URL |
| `GOOGLE_CREDENTIALS_PATH` | Yes | Path to service account JSON |
| `OPENAI_API_KEY` | No | GPT-5.2 fallback |
| `CLAUDE_MODEL` | No | Override model (proxy default: `global.anthropic.claude-opus-4-6-v1:0`, direct default: `claude-opus-4-6-20250610`) |
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

### Phantom Persona System (2026-02-11)
- **Persona Dossiers:** Created `docs/PERSONA_DOSSIERS.md` — full LinkedIn profile builds for all 6 phantom personas (Marcus Chen, Dr. Priya Nair, Jake Morrison, Rebecca Torres, Alex Kim, David Okafor). Includes headlines, About sections, experience entries, skills lists, who-to-follow lists, voice guides, example comments, interaction matrix, account warming checklist, and browser session setup.
- **Rich personas.json:** Expanded `config/personas.json` with `display_name`, `linkedin_url`, `location`, `active_hours` (timezone-aware), `voice` object (tone, vocabulary, signature_phrases, comment_length, avoids), `engagement_rules` (trigger topics, debates_with, agrees_with), and enhanced `system_prompt` encoding full backstory and voice rules per persona.
- **Persona-specific templates:** Added 90 new CommentTemplates (15 per phantom) to the spreadsheet generator (`/tmp/gen_linkedin_spreadsheet.py`). Each persona's templates are written in their distinct voice. Added `Persona` column (column G) to the CommentTemplates tab. IDs: P001-P090.
- **Phantom engagement content:** Added 29 `phantom_engagement` entries to ContentBank — pre-written multi-persona conversation threads organized by post topic (AI, ops, Python, growth, safety, content pipeline, learning). Each thread contains 3 persona comments creating natural debate.
- **Usage guide:** Created `docs/PHANTOM_SYSTEM_GUIDE.md` — human-readable usage guide covering setup, interaction matrix, modification instructions, safety rules, and current counts.
- **Spreadsheet regenerated:** LinkedIn Stealth Engine.xlsx now has 858 total data rows (CommentTemplates: 192, ContentBank: 178, CommentTargets: 180, RepostBank: 146, etc.)

---

## What Has Been Tested and Verified

1. Google Sheet connectivity — working (used for initial seed, still available via DATA_BACKEND=sheets toggle)
2. Playwright browser launch + persistent sessions — working (MainUser sessions at ~/.ai-linkedin-machine/sessions/)
3. LinkedIn DOM selectors — verified 2026-04-03 (activity page uses `div[data-urn]` fallback)
4. LLM API calls — Claude via ai-router proxy (vertex_ai/claude-opus-4-6), OpenAI GPT-5.2 fallback
5. Commenter — tested live, 404 detection added, target pool expanded
6. Replier — tested E2E, 5 bug-fix cycles, successfully posted live reply to Brian Kerrigan
7. RSS ingestion — hash manifest dedup, 7-day recency, full pipeline dry run in ~100s
8. Safety filter — 30+ blocked phrases, consulting pattern relaxed to avoid false positives
9. Kill switch — functional (STOP file in project root)

## What Has NOT Been Tested Yet

1. Phantom persona engagement (Marcus Chen is first — implementation in progress)
2. Multi-persona orchestrated engagement (phantoms commenting after MainUser posts)
3. Content generation quality (RSS → summarize → generate posts → verify)
4. Deploy to Coolify (production deployment behind reverse proxy)
5. Commenter dry-run skip (orchestrator still launches Playwright in dry-run mode)

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
