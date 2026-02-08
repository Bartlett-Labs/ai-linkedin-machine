#!/bin/bash
# Run the posting + engagement pipeline.
# Executes queued posts, comments on targets, checks replies.
# Reads configuration from Google Sheet.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"
source venv/bin/activate

# Parse arguments
DRY_RUN=""
NO_HEADLESS=""

for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN="--dry-run" ;;
        --no-headless) NO_HEADLESS="--no-headless" ;;
        --comments-only) COMMENTS_ONLY="--comments-only" ;;
        --replies-only) REPLIES_ONLY="--replies-only" ;;
    esac
done

echo "=== Running Poster + Engagement Pipeline ==="

python main.py --skip-ingest --skip-generate $DRY_RUN $NO_HEADLESS $COMMENTS_ONLY $REPLIES_ONLY

echo "=== Pipeline Complete ==="
