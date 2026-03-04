#!/usr/bin/env bash
# Wrapper script for launchd — activates venv and runs the scheduler.

PROJECT_DIR="/Volumes/Bart_26/Dev_Expansion/Personal/Career/LinkedIn/ai-linkedin-machine"

# Wait for volume to mount (relevant on boot)
for i in {1..30}; do
    [ -d "$PROJECT_DIR" ] && break
    sleep 2
done

if [ ! -d "$PROJECT_DIR" ]; then
    echo "ERROR: Volume not mounted after 60s" >&2
    exit 1
fi

cd "$PROJECT_DIR"

# Activate virtual environment
source "$PROJECT_DIR/venv/bin/activate"

# Run the scheduler
exec python scheduler.py
