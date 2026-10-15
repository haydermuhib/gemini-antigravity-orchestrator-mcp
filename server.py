#!/usr/bin/env python3
"""
Antigravity MCP Server - CLI & Remote HTTP/SSE Entry Point.
Connect Google Gemini (Cloud / Connected Apps) via public HTTPS URL or local stdio.
"""

import sys
from pathlib import Path

# Add current directory to sys.path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from antigravity_mcp.cli import main

if __name__ == "__main__":
    main()
