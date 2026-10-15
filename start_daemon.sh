#!/usr/bin/env bash
# Start Antigravity MCP Server & Cloudflare Tunnel in the background (Daemon Mode)
# This keeps the server running when you close your terminal or are away from your computer.

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
        echo "⚠️  Antigravity MCP Server is already running (PID: $PID)"
        if [ -f "$URL_FILE" ]; then
            echo "Current URL: $(cat "$URL_FILE")"
        fi
        exit 0
    else
        rm -f "$PID_FILE"
    fi
fi

echo "🚀 Starting Antigravity MCP Server with pixi & Cloudflare Tunnel in background..."

# Find pixi binary
PIXI_BIN="/home/haider/.pixi/bin/pixi"
if [ ! -f "$PIXI_BIN" ]; then
    PIXI_BIN="pixi"
fi

# Run server with pixi and tunnel in background
WS_ARG=""
if [ -n "$ANTIGRAV_WORKSPACE" ]; then
    WS_ARG="--workspace $ANTIGRAV_WORKSPACE"
fi

nohup "$PIXI_BIN" run python3 server.py --tunnel $WS_ARG > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

echo "Waiting for Cloudflare Tunnel URL to be generated..."
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
    echo ""
    echo "======================================================================"
    echo "✨ BACKGROUND MCP SERVER IS ACTIVE & READY! ✨"
    echo "👉 MCP Server URL: $TUNNEL_URL"
    echo "👉 SSE Endpoint:   $TUNNEL_URL/sse"
    echo "======================================================================"
    echo "Saved to: $URL_FILE"
    echo "Log file: $LOG_FILE"
    echo "To stop:  ./stop_daemon.sh"
    echo "======================================================================"
else
    echo "⚠️  Server started (PID: $SERVER_PID), but tunnel URL not detected yet."
    echo "Check logs with: tail -f $LOG_FILE"
fi
