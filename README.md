# AI LinkedIn Machine

An automated system that ingests AI/tech news from RSS feeds, summarizes them using LLMs, generates LinkedIn posts, and publishes them.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `LINKEDIN_EMAIL`: Your LinkedIn email
   - `LINKEDIN_PASSWORD`: Your LinkedIn password

3. Run the pipeline once:
   ```bash
   python main.py
   ```

4. For scheduled runs (daily at 9 AM):
   ```bash
   python scheduler.py
   ```

## Modules

- `ingestion/`: Fetches RSS feeds and scrapes article content
- `summarization/`: Summarizes articles using GPT-4
- `posting_generator/`: Generates LinkedIn posts from summaries
- `posting/`: Automates posting to LinkedIn
- `engagement/`: Comments on top posts, replies to comments for algorithm optimization

## Configuration

- Feeds: `config/feeds.json`
- Personas: `config/personas.json` (multiple accounts/personas for coordinated engagement)
- Rate limits: `config/rate_limits.yaml`
- App config: `config/app_config.yaml` (empty, can add settings)

## Notes

- Uses Selenium for LinkedIn automation (headless mode)
- Safety filters prevent promotional content
- Summaries are stored in `queue/summaries/`
- Generated posts in `queue/posts/`
- Engagement features: Comments on recent top posts, replies to comments on your content
- Multi-persona support: Coordinated engagement across multiple LinkedIn accounts
- Scheduler randomizes posting times (1-3 per day, 8 AM - 10 PM, avoiding 2-6 AM)
- Tracker stores interaction data in `queue/engagement/tracker.json`