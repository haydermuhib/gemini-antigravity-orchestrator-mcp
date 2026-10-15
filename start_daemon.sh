#!/usr/bin/env bash
# Start Antigravity MCP Server and Cloudflare Tunnel in background (Daemon Mode)

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

exec python3 server.py start
