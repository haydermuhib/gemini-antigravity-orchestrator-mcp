#!/usr/bin/env bash
# Stop Antigravity MCP Server background processes and tunnels

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$DIR/.server.pid"

STOPPED=false

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "[INFO] Stopping Antigravity MCP Server (PID: $PID)..."
        kill "$PID" 2>/dev/null || true
        STOPPED=true
    fi
    rm -f "$PID_FILE"
fi

# Terminate orphaned background tunnels or servers on port 8080
pkill -f "cloudflared.*8080" 2>/dev/null || true
pkill -f "server.py.*--tunnel" 2>/dev/null || true

if [ "$STOPPED" = true ]; then
    echo "[OK] Server stopped."
else
    echo "[INFO] Server was not running."
fi
