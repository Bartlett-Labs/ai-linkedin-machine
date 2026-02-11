#!/bin/bash
# AI LinkedIn Machine - Full Setup Script
# Creates venv, installs deps, sets up Playwright, creates dirs, prompts for .env

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== AI LinkedIn Machine Setup ==="
echo "Project directory: $PROJECT_DIR"
echo ""

cd "$PROJECT_DIR"

# 1. Create Python virtual environment
echo "[1/6] Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  Created venv/"
else
    echo "  venv/ already exists, skipping"
fi

# Activate venv
source venv/bin/activate

# 2. Install Python dependencies
echo "[2/6] Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  Dependencies installed"

# 3. Install Playwright browsers
echo "[3/6] Installing Playwright Chromium browser..."
playwright install chromium
echo "  Chromium installed"

# 4. Create required directories
echo "[4/6] Creating project directories..."
mkdir -p queue/incoming_raw
mkdir -p queue/summaries
mkdir -p queue/posts
mkdir -p queue/posts/done
mkdir -p queue/posts/failed
mkdir -p queue/engagement
mkdir -p tracking/linkedin
mkdir -p logs
mkdir -p credentials
mkdir -p ~/.ai-linkedin-machine/sessions
echo "  Directories created"

# 5. Set up .env file
echo "[5/6] Checking .env file..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  Created .env from .env.example"
    echo "  >>> IMPORTANT: Edit .env with your actual API keys and Sheet ID <<<"
else
    echo "  .env already exists, skipping"
fi

# 6. Verify setup
echo "[6/6] Verifying setup..."
python -c "import playwright.async_api; print('  Playwright: OK')"
python -c "from anthropic import AnthropicBedrock; print('  Anthropic SDK (Bedrock): OK')"
python -c "import openai; print('  OpenAI SDK: OK')"
python -c "import googleapiclient; print('  Google API: OK')"
python -c "import yaml; print('  PyYAML: OK')"
python -c "import feedparser; print('  feedparser: OK')"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys and Google Sheet ID"
echo "  2. Place Google service account JSON in credentials/service_account.json"
echo "  3. Log in to LinkedIn manually for each persona:"
echo "     python -c \"import asyncio; from browser.context_manager import PersonaContext; asyncio.run(PersonaContext('MainUser', headless=False).start())\""
echo "  4. Run a dry test: python main.py --dry-run --skip-ingest"
echo "  5. Run the full pipeline: python main.py"
echo ""
