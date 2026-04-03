#!/usr/bin/env bash
# AI LinkedIn Machine — process manager
# Starts both the main API and webhook service.
#
# Usage:
#   ./start.sh          # start both services
#   ./start.sh api      # start main API only
#   ./start.sh webhook  # start webhook service only
#   ./start.sh stop     # stop all services

set -euo pipefail
cd "$(dirname "$0")"

# Activate virtualenv
source venv/bin/activate

API_PORT="${API_PORT:-8000}"
WEBHOOK_PORT="${WEBHOOK_PORT:-3847}"
PID_DIR=".pids"
mkdir -p "$PID_DIR"

start_api() {
    echo "[+] Starting main API on port $API_PORT..."
    uvicorn api.server:app --host 0.0.0.0 --port "$API_PORT" &
    echo $! > "$PID_DIR/api.pid"
    echo "    PID: $(cat "$PID_DIR/api.pid")"
}

start_webhook() {
    echo "[+] Starting webhook service on port $WEBHOOK_PORT..."
    uvicorn webhook.server:app --host 0.0.0.0 --port "$WEBHOOK_PORT" &
    echo $! > "$PID_DIR/webhook.pid"
    echo "    PID: $(cat "$PID_DIR/webhook.pid")"
}

stop_all() {
    echo "[x] Stopping services..."
    for pidfile in "$PID_DIR"/*.pid; do
        [ -f "$pidfile" ] || continue
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            echo "    Stopped PID $pid ($(basename "$pidfile" .pid))"
        fi
        rm -f "$pidfile"
    done
}

case "${1:-all}" in
    api)
        start_api
        ;;
    webhook)
        start_webhook
        ;;
    stop)
        stop_all
        exit 0
        ;;
    all)
        start_api
        start_webhook
        ;;
    *)
        echo "Usage: $0 {api|webhook|stop|all}"
        exit 1
        ;;
esac

echo ""
echo "Services running. Use './start.sh stop' to shut down."
echo "  Main API:  http://localhost:$API_PORT/api/health"
echo "  Webhook:   http://localhost:$WEBHOOK_PORT/health"
wait
