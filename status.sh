#!/usr/bin/env bash
# Check status of the Antigravity MCP Server background daemon

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

exec python3 server.py status
