#!/usr/bin/env bash
# Stop Antigravity MCP Server background processes and tunnels

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

python3 server.py stop
pkill -f "cloudflared.*8080" 2>/dev/null || true
pkill -f "antigravity_mcp.cli.*--tunnel" 2>/dev/null || true
