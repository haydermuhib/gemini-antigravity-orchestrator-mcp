#!/usr/bin/env python3
"""
Antigravity MCP Server - CLI & Remote HTTP/SSE Entry Point.
Connect Google Gemini (Cloud / Connected Apps) via public HTTPS URL or local stdio.
"""

import os
import sys
import time
import argparse
import subprocess
import threading
from pathlib import Path

# Add current directory to sys.path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from antigravity_mcp.server import MCPServer
from antigravity_mcp.http_server import start_http_server


def start_tunnel_process(port: int):
    """Spawns cloudflared tunnel to expose local HTTP port over public HTTPS without password."""
    cloudflared_bin = subprocess.run(["which", "cloudflared"], capture_output=True, text=True).stdout.strip()
    if not cloudflared_bin:
        sys.stderr.write("[Tunnel Warning] 'cloudflared' binary not found. Install cloudflared to auto-tunnel.\n")
        return None

    sys.stderr.write(f"\n🌐 Launching Cloudflare Tunnel for http://localhost:{port}...\n")
    proc = subprocess.Popen(
        [cloudflared_bin, "tunnel", "--url", f"http://127.0.0.1:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Monitor stderr where cloudflared logs the assigned https://*.trycloudflare.com URL
    def monitor_tunnel():
        tunnel_url = None
        for line in proc.stderr:
            sys.stderr.write(line)
            if "trycloudflare.com" in line and not tunnel_url:
                for part in line.split():
                    if part.startswith("https://") and "trycloudflare.com" in part:
                        tunnel_url = part.strip()
                        print("\n" + "=" * 70, flush=True)
                        print("✨ GOOGLE GEMINI MCP SERVER PUBLIC URL READY! ✨", flush=True)
                        print(f"👉 MCP Server URL: {tunnel_url}", flush=True)
                        print(f"👉 SSE Endpoint:   {tunnel_url}/sse", flush=True)
                        print("=" * 70, flush=True)
                        print("Copy and paste the URL above into Google Gemini's 'MCP server URL' box.\n", flush=True)
                        break

    t = threading.Thread(target=monitor_tunnel, daemon=True)
    t.start()
    return proc


def main():
    parser = argparse.ArgumentParser(
        description="Antigravity MCP Server - Model Context Protocol for Google Gemini & Antigravity IDE"
    )
    parser.add_argument(
        "--workspace",
        "-w",
        default=str(current_dir),
        help="Workspace root path to monitor and orchestrate (defaults to current directory)."
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run as HTTP / SSE Server (required for Google Gemini Cloud Connected Apps)."
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8080,
        help="Port for HTTP server (default: 8080)."
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host address for HTTP server (default: 0.0.0.0)."
    )
    parser.add_argument(
        "--tunnel",
        "-t",
        action="store_true",
        help="Automatically launch a free public HTTPS Cloudflare Tunnel for Google Gemini."
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Force Stdio JSON-RPC transport (used by local CLI clients)."
    )

    args = parser.parse_args()

    # Determine mode: if --http or --tunnel or stdout is a terminal, run HTTP
    run_http = args.http or args.tunnel or (not args.stdio and sys.stdin.isatty())

    if run_http:
        print("\n" + "=" * 70)
        print("🚀 Starting Antigravity MCP Server in HTTP / SSE Mode")
        print(f"   Local Address: http://localhost:{args.port}")
        print(f"   SSE Endpoint:  http://localhost:{args.port}/sse")
        print("=" * 70)

        if args.tunnel:
            start_tunnel_process(args.port)
        else:
            print("\n💡 Tip: To generate a public https:// URL for Google Gemini, run:")
            print(f"   python3 server.py --tunnel\n")

        start_http_server(host=args.host, port=args.port, workspace_root=args.workspace)
    else:
        # Standard Stdio mode
        server = MCPServer(workspace_root=args.workspace)
        server.run()


if __name__ == "__main__":
    main()
