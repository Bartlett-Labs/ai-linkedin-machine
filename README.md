# AI LinkedIn Machine

A three-layer automated LinkedIn brand-building system that ingests AI/tech news, generates original posts, publishes them via browser automation, and coordinates multi-persona engagement to maximize reach during the "golden hour."

---

## How It Works

The system has three layers that work together:

### Layer 1: Google Sheet ("LinkedIn Stealth Engine")
The brain. A live Google Sheet with 10 tabs that stores everything: queued post drafts, comment targets, comment templates, reply rules, safety terms, scheduling config, engine control settings, and a full system log. You control the system by editing the Sheet — change the phase, pause the engine, add comment targets, update safety terms. The Python code reads from and writes to this Sheet.

### Layer 2: Python Execution Engine (this repo)
The muscle. Reads queued items from the Sheet, executes them on LinkedIn using Playwright browser automation, and logs results back to the Sheet. Also handles RSS ingestion, article summarization, and post generation using Claude (Opus 4.6) as the primary LLM.

### Layer 3: Playwright Browser Automation
The hands. Each persona gets its own persistent browser session with saved cookies, so logins survive between runs. Human-like typing simulation (random delays, occasional typos, correction pauses) makes interactions look organic. Challenge/CAPTCHA detection triggers an automatic kill switch if LinkedIn gets suspicious.

---

## Architecture

```
RSS Feeds ──> Ingest ──> Summarize ──> Generate Post ──> OutboundQueue (Sheet)
                              |                                |
                         Claude Opus 4.6                       |
                                                               v
                                                    Orchestrator reads queue
                                                               |
                              ┌─────────────────┬──────────────┼──────────────┐
                              v                 v              v              v
                         MainUser Post    Phantom Engage   Comment on     Reply to
                         (Playwright)     (Like + Comment   Targets       Comments
                                          2-15 min later)  (7-12/day)    on own posts
                              |                 |              |              |
                              └─────────────────┴──────────────┴──────────────┘
                                                               |
                                                               v
                                                    Sheet SystemLog + Local Tracking
```

---

## Personas

The system runs 7 personas, each with its own LinkedIn account, browser session, voice, and engagement style:

| Persona | Role | Purpose |
|---------|------|---------|
| **MainUser** | Demand Planner / AI practitioner | Your actual account. Posts content, comments on targets, replies to engagement |
| The Visionary Advisor | Startup advisor | Comments with big-picture strategic takes |
| The Deep Learner | AI researcher | Comments with technical depth, academic tone |
| The Skeptical Senior Dev | Pragmatic engineer | Comments with contrarian, anti-hype perspective |
| The Corporate Compliance Officer | Legal/risk professional | Comments on compliance, privacy, regulatory angles |
| The Creative Tinkerer | Hobbyist developer | Comments with enthusiasm about DIY and unconventional uses |
| The ROI-Driven Manager | Operations manager | Comments focused on cost savings and time efficiency |

The phantom personas engage on MainUser's posts after a randomized delay (2-15 minutes) to simulate organic engagement during the golden hour (first 60-90 minutes = 70% of post reach).

---

## Phases

The system operates in three phases, controlled via the Sheet's EngineControl tab:

| Phase | Posting | Comments/Day | Phantom Comments/Post | Delay Between Actions |
|-------|---------|-------------|----------------------|----------------------|
| **Stealth** | 2/week | 10 | 2 | 5 min |
| **Announcement** | 2/day | 15 | 4 | 3 min |
| **Authority** | 2/day | 12 | 6 | 2 min |

---

## Safety System

Safety is enforced at multiple levels because the user is a Demand Planner at Anker and content must never:

- Claim false titles (especially "AI Automation Manager" — an offer that was rescinded)
- Reference the employer by name or reveal internal systems/processes
- Signal job searching ("open to work", "looking for opportunities", etc.)
- Solicit business ("hire me", "consulting", "freelance", etc.)
- Use engagement bait ("Agree?", "Repost if you", etc.)
- Start with generic AI-sounding praise ("Great post!", "Love this!")

**Where safety is enforced:**
1. `SAFETY_PREAMBLE` injected into every LLM system prompt (pre-generation blocking)
2. `summarization/safety_filter.py` checks all generated content against 30+ blocked phrases (post-generation blocking)
3. SafetyTerms tab in the Sheet (dynamic — add new terms without code changes)
4. `engagement/quality_checker.py` validates comment quality on 8 dimensions before posting

---

## Setup

### Prerequisites
- Python 3.11+
- A Google Cloud service account with Sheets API access
- Anthropic API key (Claude Opus 4.6)
- OpenAI API key (fallback only)
- LinkedIn accounts with existing sessions (manual login required once per persona)

### Installation

```bash
# Clone the repo
git clone https://github.com/kyle-bartlett/ai-linkedin-machine.git
cd ai-linkedin-machine

# Run the setup script (creates venv, installs deps, installs Chromium)
bash scripts/init.sh

# Or do it manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Create required directories
mkdir -p logs queue/{incoming_raw,summaries,posts,engagement} tracking/linkedin credentials
```

### Configuration

1. Copy `.env.example` to `.env` and fill in your keys:
   ```bash
   cp .env.example .env
   ```
   Required variables:
   - `ANTHROPIC_API_KEY` — Your Anthropic key (primary LLM)
   - `GOOGLE_SHEET_ID` — The Sheet ID from the URL
   - `GOOGLE_CREDENTIALS_PATH` — Path to your service account JSON

2. Place your Google service account JSON in `credentials/service_account.json`

3. Log in to LinkedIn manually for each persona (first run with `--no-headless`):
   ```bash
   python main.py --no-headless --dry-run
   ```
   The session cookies are saved to `~/.ai-linkedin-machine/sessions/{persona_name}/` and persist between runs.

---

## Usage

### Full pipeline (ingest + generate + post + engage)
```bash
python main.py
```

### Dry run (generates everything, executes nothing on LinkedIn)
```bash
python main.py --dry-run
```

### Skip ingestion (just execute queued items)
```bash
python main.py --skip-ingest --skip-generate
```

### Comments only
```bash
python main.py --comments-only
```

### Replies only
```bash
python main.py --replies-only
```

### Show browser windows (debug mode)
```bash
python main.py --no-headless
```

### Scheduled runs
```bash
python scheduler.py
```

### Emergency stop
```bash
touch STOP          # Halt everything immediately
rm STOP             # Resume operations
```

---

## Project Structure

```
ai-linkedin-machine/
├── browser/                    # Playwright browser automation
│   ├── context_manager.py      # Persistent browser contexts per persona
│   ├── human_typing.py         # Human-like typing simulation
│   └── linkedin_actions.py     # LinkedIn DOM interactions + challenge detection
├── config/
│   ├── app_config.yaml         # Core settings (timezone, paths, LLM config)
│   ├── feeds.json              # RSS feed sources
│   ├── personas.json           # 7 persona definitions with system prompts
│   └── rate_limits.yaml        # Phase-based rate limits
├── engagement/
│   ├── commenter.py            # Comment on target posts (interleaved browsing)
│   ├── lead_tracker.py         # Identify and track potential leads
│   ├── quality_checker.py      # 8-dimension comment quality validation
│   ├── replier.py              # Reply to comments on own posts
│   └── tracker.py              # Local daily activity tracking (secondary log)
├── ingestion/
│   ├── rss_ingest.py           # RSS feed ingestion
│   ├── arxiv_ingest.py         # ArXiv paper ingestion
│   ├── web_scraper.py          # General web scraping
│   └── youtube_ingest.py       # YouTube transcript ingestion
├── llm/
│   └── provider.py             # LLM abstraction: Claude -> OpenAI -> templates
├── posting/
│   └── poster.py               # Execute posts via Playwright
├── posting_generator/
│   └── generate_post.py        # Generate LinkedIn posts from summaries
├── scheduling/
│   ├── content_calendar.py     # Weekly content planning + posting windows
│   └── orchestrator.py         # Main coordinator for all actions
├── sheets/
│   ├── client.py               # Google Sheets API integration
│   └── models.py               # Data models matching Sheet schema
├── summarization/
│   ├── safety_filter.py        # Content safety checking (30+ blocked phrases)
│   ├── summarize.py            # Article summarization via LLM
│   └── prompt_templates/       # LLM prompt templates
├── utils/
│   ├── dedup.py                # Content deduplication (Jaccard similarity)
│   ├── kill_switch.py          # Local STOP file emergency halt
│   └── retry.py                # Exponential backoff for transient failures
├── scripts/
│   ├── init.sh                 # Full setup script
│   ├── run_ingest.sh           # Ingestion pipeline only
│   └── run_poster.sh           # Posting + engagement pipeline
├── main.py                     # Async pipeline entry point
├── scheduler.py                # Scheduled runs (thin wrapper around orchestrator)
├── requirements.txt            # Python dependencies
└── .env.example                # Environment variable documentation
```

---

## LLM Stack

| Provider | Model | Role |
|----------|-------|------|
| **Anthropic** | Claude Opus 4.6 (`claude-opus-4-6-20250610`) | Primary. All comments, replies, posts, summaries |
| OpenAI | GPT-5.2 | Fallback only. Used if Anthropic API is unavailable |
| Templates | Sheet CommentTemplates tab | Last resort. Used if both APIs fail |

---

## Key Design Decisions

- **Google Sheet is the brain, Python is the executor.** All targeting, templates, safety terms, and scheduling logic lives in the Sheet. Change strategy without touching code.
- **Persistent browser sessions.** Cookies survive between runs. No re-login every time.
- **Pre-generation safety.** Safety rules are injected into every LLM system prompt, not just checked after generation. The model avoids blocked content during generation.
- **Interleaved browsing.** The commenter alternates between target visits and feed scrolling to look more organic. Every 3rd action comes from the feed.
- **Kill switch works offline.** A local `STOP` file halts everything even if the Sheet or API is unreachable. Also activates automatically when LinkedIn challenges are detected.
- **Quality over quantity.** Comments are validated against 8 quality dimensions and scored 0-100. Anything under 60 gets regenerated with feedback. Anything that still fails gets skipped.
