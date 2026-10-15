#!/usr/bin/env bash
# Start Antigravity MCP Server and Cloudflare Tunnel in background (Daemon Mode)

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

PID_FILE="$DIR/.server.pid"
LOG_FILE="$DIR/mcp_server.log"
URL_FILE="$DIR/current_tunnel_url.txt"

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "[INFO] Server is already running (PID: $PID)"
        if [ -f "$URL_FILE" ]; then
            echo "[INFO] Current URL: $(cat "$URL_FILE")"
        fi
        exit 0
    else
        rm -f "$PID_FILE"
    fi
fi

echo "[INFO] Starting Antigravity MCP Server and Cloudflare tunnel in background..."

# Resolve pixi or python3
RUN_CMD="python3 server.py --tunnel"
if command -v pixi &> /dev/null; then
    RUN_CMD="pixi run python3 server.py --tunnel"
fi

WS_ARG=""
if [ -n "$ANTIGRAV_WORKSPACE" ]; then
    WS_ARG="--workspace $ANTIGRAV_WORKSPACE"
fi

nohup $RUN_CMD $WS_ARG > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

echo "[INFO] Waiting for public tunnel URL..."
TUNNEL_URL=""
for i in {1..30}; do
    sleep 1
    if grep -q "Your quick Tunnel has been created" "$LOG_FILE" 2>/dev/null; then
        TUNNEL_URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "$LOG_FILE" | grep -v 'api.trycloudflare.com' | head -n 1 || true)
        if [ -n "$TUNNEL_URL" ]; then
            break
        fi
    fi
done

if [ -n "$TUNNEL_URL" ]; then
    echo "$TUNNEL_URL" > "$URL_FILE"
    echo "--------------------------------------------------"
    echo "[OK] Server running (PID: $SERVER_PID)"
    echo "Server URL:   $TUNNEL_URL"
    echo "SSE Endpoint: $TUNNEL_URL/sse"
    echo "Log file:     $LOG_FILE"
    echo "To stop:      ./stop_daemon.sh"
    echo "--------------------------------------------------"
else
    echo "[WARN] Server started (PID: $SERVER_PID), but tunnel URL not yet detected."
    echo "[INFO] Check logs with: tail -f $LOG_FILE"
fi
