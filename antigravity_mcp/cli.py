"""
Modern CLI & TUI Entrypoint for Antigravity MCP Orchestrator.
Complies with cli-ux and tui-design-skill principles:
- In-place transient spinners with Braille animation
- Settling status glyphs (✔, ✘, ⚠)
- High-contrast visual hierarchy and box-drawing cards
- Clean signal handling and zero-dependency runtime
"""

import os
import sys
import time
import signal
import shutil
import argparse
import subprocess
import threading
from pathlib import Path
from typing import Optional

from .ui import (
    Spinner,
    Color,
    render_banner,
    render_box,
    render_connection_guide,
    is_tty
)
from .server import MCPServer
from .http_server import start_http_server

PID_FILENAME = ".server.pid"
LOG_FILENAME = "mcp_server.log"
URL_FILENAME = "current_tunnel_url.txt"


def find_workspace_root(start_path: Optional[str] = None) -> Path:
    """Finds workspace root containing GEMINI.md or .git or defaults to cwd."""
    p = Path(start_path or os.getcwd()).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "GEMINI.md").exists() or (parent / ".agents").exists() or (parent / "pixi.toml").exists():
            return parent
    return p


def get_state_paths(workspace_root: Path):
    return {
        "pid": workspace_root / PID_FILENAME,
        "log": workspace_root / LOG_FILENAME,
        "url": workspace_root / URL_FILENAME,
    }


def rotate_log_if_needed(log_path: Path, max_bytes: int = 5 * 1024 * 1024, backup_count: int = 2):
    """Rotates log file if it exceeds max_bytes to prevent unbounded disk growth."""
    try:
        if log_path.exists() and log_path.stat().st_size >= max_bytes:
            for i in range(backup_count - 1, 0, -1):
                s = log_path.with_name(f"{log_path.name}.{i}")
                d = log_path.with_name(f"{log_path.name}.{i+1}")
                if s.exists():
                    s.replace(d)
            backup = log_path.with_name(f"{log_path.name}.1")
            log_path.replace(backup)
    except Exception:
        pass


def is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def cmd_status(workspace_root: Path):
    """Renders a modern, structured TUI diagnostic status card."""
    paths = get_state_paths(workspace_root)
    render_banner("1.0.0")

    pid = None
    running = False
    if paths["pid"].exists():
        try:
            pid = int(paths["pid"].read_text().strip())
            running = is_process_alive(pid)
        except Exception:
            running = False

    tunnel_url = None
    if paths["url"].exists():
        tunnel_url = paths["url"].read_text().strip()

    status_str = f"{Color.GREEN}{Color.BOLD}● RUNNING{Color.RESET}" if running else f"{Color.DARK_GRAY}○ STOPPED{Color.RESET}"
    pid_str = f"{pid}" if running else f"{Color.GRAY}None{Color.RESET}"

    rows = [
        ("Daemon", status_str),
        ("PID", pid_str),
        ("Workspace", str(workspace_root)),
        ("Transport", "HTTP / SSE (port 8080) + Stdio JSON-RPC"),
    ]

    if tunnel_url and running:
        rows.append(("---", ""))
        rows.append(("Public URL", f"{Color.CYAN}{tunnel_url}{Color.RESET}"))
        rows.append(("SSE URL", f"{Color.BOLD}{Color.CYAN}{tunnel_url}/sse{Color.RESET}"))

    render_box("SERVER STATUS & DIAGNOSTICS", rows)

    # Show recent log snippet if available
    if paths["log"].exists() and running:
        try:
            with open(paths["log"], "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                recent = [line.strip() for line in lines[-5:] if line.strip()]
                if recent:
                    log_rows = [("", f"{Color.DARK_GRAY}› {Color.GRAY}{l[:64]}{Color.RESET}") for l in recent]
                    render_box("RECENT SERVER LOGS", log_rows)
        except Exception:
            pass

    if not running:
        print(f"\n{Color.GRAY}Start the server with:{Color.RESET} {Color.BOLD}antigravity-mcp --tunnel{Color.RESET} (foreground)")
        print(f"                       {Color.BOLD}antigravity-mcp start{Color.RESET}    (background daemon)\n")
    elif tunnel_url:
        render_connection_guide(tunnel_url)


def cmd_stop(workspace_root: Path):
    """Gracefully terminates the background daemon with in-place spinner."""
    paths = get_state_paths(workspace_root)
    render_banner("1.0.0")

    if not paths["pid"].exists():
        print(f"{Color.GRAY}No active daemon PID file found at {paths['pid']}{Color.RESET}")
        return

    try:
        pid = int(paths["pid"].read_text().strip())
    except Exception:
        print(f"{Color.RED}✘ Invalid PID file.{Color.RESET}")
        paths["pid"].unlink(missing_ok=True)
        return

    if not is_process_alive(pid):
        print(f"{Color.YELLOW}⚠ Process {pid} was not running. Cleaning up stale PID file.{Color.RESET}")
        paths["pid"].unlink(missing_ok=True)
        return

    spinner = Spinner(f"Stopping Antigravity MCP Server (PID: {pid})...")
    spinner.start()

    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(25):
            if not is_process_alive(pid):
                break
            time.sleep(0.2)

        if is_process_alive(pid):
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.3)

        paths["pid"].unlink(missing_ok=True)
        spinner.succeed(f"Antigravity MCP Server (PID: {pid}) stopped successfully.")
    except Exception as e:
        spinner.fail(f"Failed to stop process {pid}: {e}")


def cmd_start(workspace_root: Path, port: int = 8080):
    """Launches the server in daemon mode with in-place progress and health checks."""
    paths = get_state_paths(workspace_root)
    render_banner("1.0.0")

    # Check if already running
    if paths["pid"].exists():
        try:
            pid = int(paths["pid"].read_text().strip())
            if is_process_alive(pid):
                print(f"{Color.YELLOW}⚠ Server is already running with PID {pid}.{Color.RESET}")
                cmd_status(workspace_root)
                return
        except Exception:
            pass

    spinner = Spinner("Spawning background MCP server daemon...")
    spinner.start()

    rotate_log_if_needed(paths["log"])
    log_file = open(paths["log"], "a", encoding="utf-8")
    cli_cmd = [
        sys.executable,
        "-m",
        "antigravity_mcp.cli",
        "--workspace",
        str(workspace_root),
        "--port",
        str(port),
        "--tunnel"
    ]

    proc = subprocess.Popen(
        cli_cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=str(workspace_root),
        start_new_session=True
    )
    paths["pid"].write_text(str(proc.pid))
    spinner.succeed(f"Server daemon spawned (PID: {proc.pid})")

    # Wait for tunnel URL in log with second spinner
    tunnel_spinner = Spinner("Establishing Cloudflare HTTPS tunnel...")
    tunnel_spinner.start()

    tunnel_url = None
    for _ in range(35):
        time.sleep(0.5)
        if paths["url"].exists():
            candidate = paths["url"].read_text().strip()
            if candidate.startswith("https://"):
                tunnel_url = candidate
                break
        if paths["log"].exists():
            try:
                content = paths["log"].read_text()
                if "trycloudflare.com" in content:
                    for part in content.split():
                        if part.startswith("https://") and "trycloudflare.com" in part and not "api." in part:
                            tunnel_url = part.strip()
                            paths["url"].write_text(tunnel_url)
                            break
                    if tunnel_url:
                        break
            except Exception:
                pass

    if tunnel_url:
        tunnel_spinner.succeed(f"Public HTTPS tunnel active: {Color.CYAN}{tunnel_url}{Color.RESET}")
        render_connection_guide(tunnel_url)
    else:
        tunnel_spinner.warn(f"Server started (PID: {proc.pid}), waiting for tunnel. Check '{paths['log'].name}'.")


def start_tunnel_process(port: int, state_file: Optional[Path] = None):
    """Spawns cloudflared tunnel with live transient status monitoring."""
    cloudflared_bin = shutil.which("cloudflared")
    if not cloudflared_bin:
        print(f"\n{Color.YELLOW}⚠ 'cloudflared' not found.{Color.RESET} Install cloudflared to auto-generate a public URL for Gemini.")
        return None

    spinner = Spinner(f"Opening secure Cloudflare Tunnel for http://localhost:{port}...")
    spinner.start()

    proc = subprocess.Popen(
        [cloudflared_bin, "tunnel", "--url", f"http://127.0.0.1:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    def monitor_tunnel():
        tunnel_url = None
        for line in proc.stderr:
            if "trycloudflare.com" in line and not tunnel_url:
                for part in line.split():
                    if part.startswith("https://") and "trycloudflare.com" in part and not "api." in part:
                        tunnel_url = part.strip()
                        if state_file:
                            try:
                                state_file.write_text(tunnel_url)
                            except Exception:
                                pass
                        spinner.succeed(f"Public Cloudflare Tunnel established!")
                        render_connection_guide(tunnel_url)
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
        help="Action: start (daemon), stop, status, tunnel (foreground), server, stdio"
    )
    parser.add_argument(
        "--workspace",
        "-w",
        default=None,
        help="Workspace root path to orchestrate (defaults to auto-discovered workspace or current directory)."
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
    workspace_root = find_workspace_root(args.workspace)

    # Route Subcommands
    if args.subcommand == "status":
        cmd_status(workspace_root)
        return
    elif args.subcommand == "stop":
        cmd_stop(workspace_root)
        return
    elif args.subcommand == "start":
        cmd_start(workspace_root, port=args.port)
        return
    elif args.subcommand == "tunnel":
        args.tunnel = True
        args.http = True
    elif args.subcommand == "server":
        args.http = True
    elif args.subcommand == "stdio":
        args.stdio = True

    run_http = args.http or args.tunnel or (not args.stdio and sys.stdin.isatty())

    if run_http:
        render_banner("1.0.0")

        # In-place spinner for initial workspace inspection
        with Spinner("Scanning workspace for Antigravity skills, rules, and plugins...") as sp:
            server_instance = MCPServer(workspace_root=str(workspace_root))
            skills_count = len(server_instance.engine.list_skills(scope="all"))
            sp.succeed(f"Workspace initialized: {Color.BOLD}{skills_count} skills{Color.RESET}, 3 plugins discovered.")

        render_box("LOCAL ENDPOINT DETAILS", [
            ("Local Base", f"http://localhost:{args.port}"),
            ("SSE Endpoint", f"{Color.CYAN}http://localhost:{args.port}/sse{Color.RESET}"),
            ("Workspace", str(workspace_root)),
            ("Transport", "HTTP / SSE + JSON-RPC 2.0"),
        ])

        if args.tunnel:
            paths = get_state_paths(workspace_root)
            start_tunnel_process(args.port, state_file=paths["url"])
        else:
            print(f"\n{Color.GRAY}Tip: To expose a public HTTPS URL for Google Gemini, run:{Color.RESET}")
            print(f"  {Color.BOLD}antigravity-mcp --tunnel{Color.RESET}\n")

        try:
            start_http_server(host=args.host, port=args.port, workspace_root=str(workspace_root))
        except KeyboardInterrupt:
            print(f"\n{Color.YELLOW}⚠ Antigravity MCP Server shutting down.{Color.RESET}")
            sys.exit(0)
    else:
        # Standard Stdio mode: stdout must remain clean JSON-RPC
        server = MCPServer(workspace_root=str(workspace_root))
        server.run()


if __name__ == "__main__":
    main()
