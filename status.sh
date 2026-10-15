#!/usr/bin/env bash
# Check status of the Antigravity MCP Server background daemon.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$DIR/.server.pid"
LOG_FILE="$DIR/mcp_server.log"
URL_FILE="$DIR/current_tunnel_url.txt"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "🟢 Antigravity MCP Server is RUNNING (PID: $PID)"
        if [ -f "$URL_FILE" ]; then
            URL=$(cat "$URL_FILE")
            echo "👉 Active Public URL: $URL"
            echo "👉 SSE Endpoint:      $URL/sse"
        fi
        echo ""
        echo "Recent log output:"
        echo "--------------------------------------------------"
        tail -n 10 "$LOG_FILE" 2>/dev/null || echo "(no logs yet)"
        echo "--------------------------------------------------"
        exit 0
    fi
fi

echo "🔴 Antigravity MCP Server is NOT running."
echo "Start it with: ./start_daemon.sh"
