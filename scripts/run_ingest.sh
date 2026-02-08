#!/bin/bash
# Run the ingestion pipeline only (RSS -> scrape -> summarize -> generate posts)
# No browser automation, no LinkedIn interaction.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"
source venv/bin/activate

echo "=== Running Ingestion Pipeline ==="

echo "[1/3] Ingesting RSS feeds..."
python -m ingestion.rss_ingest

echo "[2/3] Summarizing articles..."
python -m summarization.summarize

echo "[3/3] Generating LinkedIn posts..."
python -m posting_generator.generate_post

echo "=== Ingestion Complete ==="
echo "Posts ready in: queue/posts/"
