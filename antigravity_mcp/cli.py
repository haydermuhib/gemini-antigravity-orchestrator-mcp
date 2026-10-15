"""
Antigravity MCP CLI Entrypoint for PyPI / console_scripts.
"""

import os
import sys
import argparse
import subprocess
import threading
import shutil
from pathlib import Path

from .server import MCPServer
from .http_server import start_http_server


def start_tunnel_process(port: int):
    """Spawns cloudflared tunnel to expose local HTTP port over public HTTPS."""
    cloudflared_bin = shutil.which("cloudflared")
    if not cloudflared_bin:
        sys.stderr.write("[Tunnel Warning] 'cloudflared' not found. Install cloudflared to auto-tunnel.\n")
        return None

    sys.stderr.write(f"\n[INFO] Launching Cloudflare Tunnel for http://localhost:{port}...\n")
    proc = subprocess.Popen(
        [cloudflared_bin, "tunnel", "--url", f"http://127.0.0.1:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    def monitor_tunnel():
        tunnel_url = None
        for line in proc.stderr:
            sys.stderr.write(line)
            if "trycloudflare.com" in line and not tunnel_url:
                for part in line.split():
                    if part.startswith("https://") and "trycloudflare.com" in part:
                        tunnel_url = part.strip()
                        print("\n" + "=" * 60, flush=True)
                        print("GOOGLE GEMINI MCP PUBLIC HTTPS URL READY", flush=True)
                        print(f"MCP Server URL: {tunnel_url}", flush=True)
                        print(f"SSE Endpoint:   {tunnel_url}/sse", flush=True)
                        print("=" * 60, flush=True)
                        print("Copy and paste this URL into Google Gemini's Connected Apps box.\n", flush=True)
                        break

    t = threading.Thread(target=monitor_tunnel, daemon=True)
    t.start()
    return proc


def main():
    parser = argparse.ArgumentParser(
        prog="antigravity-mcp",
        description="Antigravity MCP Server - Model Context Protocol for Google Gemini & Antigravity IDE"
    )
    parser.add_argument(
        "subcommand",
        nargs="?",
        choices=["start", "stop", "status", "tunnel", "server", "stdio"],
        help="Optional action: tunnel, server, stdio"
    )
    parser.add_argument(
        "--workspace",
        "-w",
        default=os.getcwd(),
        help="Workspace root path to orchestrate (defaults to current directory)."
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
        help="Force Stdio JSON-RPC transport (used by local IDEs and CLI clients)."
    )

    args, unknown = parser.parse_known_args()

    # Handle subcommands
    if args.subcommand == "tunnel":
        args.tunnel = True
        args.http = True
    elif args.subcommand == "server":
        args.http = True
    elif args.subcommand == "stdio":
        args.stdio = True

    run_http = args.http or args.tunnel or (not args.stdio and sys.stdin.isatty())

    if run_http:
        print("\n" + "=" * 60)
        print("Starting Antigravity MCP Server in HTTP / SSE Mode")
        print(f"Local Address: http://localhost:{args.port}")
        print(f"SSE Endpoint:  http://localhost:{args.port}/sse")
        print("=" * 60)

        if args.tunnel:
            start_tunnel_process(args.port)
        else:
            print("\nTip: To generate a public https:// URL for Google Gemini, run:")
            print(f"  antigravity-mcp --tunnel\n")

        start_http_server(host=args.host, port=args.port, workspace_root=args.workspace)
    else:
        server = MCPServer(workspace_root=args.workspace)
        server.run()


if __name__ == "__main__":
    main()
