"""
Modern CLI-UX and TUI Components for Antigravity MCP Orchestrator.
Zero external dependencies, standard library only, full TTY/ANSI detection.
"""

import os
import sys
import time
import shutil
import threading
from typing import Optional, List


def is_tty() -> bool:
    """Returns True if stdout is an interactive terminal and TERM is not dumb."""
    if not sys.stdout.isatty() or os.environ.get("TERM", "") == "dumb":
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
                return True
        except Exception:
            return os.environ.get("WT_SESSION") is not None
    return True


class Color:
    """ANSI 256-color and basic style codes with automatic TTY degradation."""
    _enabled = is_tty()

    RESET = "\033[0m" if _enabled else ""
    BOLD = "\033[1m" if _enabled else ""
    DIM = "\033[2m" if _enabled else ""
    ITALIC = "\033[3m" if _enabled else ""
    UNDERLINE = "\033[4m" if _enabled else ""

    # Foreground
    RED = "\033[38;5;196m" if _enabled else ""
    GREEN = "\033[38;5;46m" if _enabled else ""
    YELLOW = "\033[38;5;220m" if _enabled else ""
    BLUE = "\033[38;5;39m" if _enabled else ""
    MAGENTA = "\033[38;5;201m" if _enabled else ""
    CYAN = "\033[38;5;51m" if _enabled else ""
    WHITE = "\033[38;5;255m" if _enabled else ""
    GRAY = "\033[38;5;244m" if _enabled else ""
    DARK_GRAY = "\033[38;5;238m" if _enabled else ""

    # Background
    BG_DARK = "\033[48;5;234m" if _enabled else ""
    BG_RED = "\033[48;5;196m" if _enabled else ""
    BG_GREEN = "\033[48;5;28m" if _enabled else ""


class Spinner:
    """
    Animated in-place terminal spinner conforming to cli-ux specifications.
    Uses Braille dots, transient in-place updates, and settles cleanly on exit.
    """
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str, delay: float = 0.08):
        self.message = message
        self.delay = delay
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_running = False
        self._tty = is_tty()

    def _spin(self):
        idx = 0
        while not self._stop_event.is_set():
            frame = self.FRAMES[idx % len(self.FRAMES)]
            # Overwrite line in-place using carriage return and clear-to-eol
            line = f"\r{Color.CYAN}{frame}{Color.RESET} {self.message}"
            sys.stdout.write(line)
            sys.stdout.flush()
            idx += 1
            time.sleep(self.delay)

    def start(self):
        """Starts the background animation."""
        if self._is_running:
            return self
        if not self._tty:
            sys.stdout.write(f"[...] {self.message}\n")
            sys.stdout.flush()
            self._is_running = True
            return self

        # Hide cursor
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        self._is_running = True
        return self

    def update(self, new_message: str):
        """Updates the ongoing spinner text."""
        self.message = new_message
        if not self._tty:
            sys.stdout.write(f"[...] {self.message}\n")
            sys.stdout.flush()

    def succeed(self, final_message: Optional[str] = None):
        """Cleans up spinner and writes permanent checkmark."""
        msg = final_message or self.message
        self._finish(f"{Color.GREEN}✔{Color.RESET} {msg}\n")

    def fail(self, final_message: Optional[str] = None):
        """Cleans up spinner and writes permanent error cross."""
        msg = final_message or self.message
        self._finish(f"{Color.RED}✘{Color.RESET} {msg}\n")

    def warn(self, final_message: Optional[str] = None):
        """Cleans up spinner and writes permanent warning indicator."""
        msg = final_message or self.message
        self._finish(f"{Color.YELLOW}⚠{Color.RESET} {msg}\n")

    def _finish(self, output: str):
        if not self._is_running:
            return
        if self._tty:
            self._stop_event.set()
            if self._thread:
                self._thread.join(timeout=0.5)
            # Clear current line and show cursor
            sys.stdout.write("\r\033[K" + output + "\033[?25h")
            sys.stdout.flush()
        else:
            sys.stdout.write(output)
            sys.stdout.flush()
        self._is_running = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.fail(f"{self.message} (failed: {exc_val})")
        else:
            self.succeed()


def get_terminal_width(default: int = 70) -> int:
    """Returns safe width for formatting bounded between 40 and 80 columns."""
    try:
        cols, _ = shutil.get_terminal_size((default, 24))
        return min(max(cols - 2, 40), 76)
    except Exception:
        return default


def render_banner(version: str = "1.0.0") -> None:
    """Renders high-contrast modern retro-terminal banner."""
    w = get_terminal_width()
    inner = w - 4

    c_border = Color.DARK_GRAY
    c_title = Color.BOLD + Color.RED
    c_sub = Color.GRAY
    c_v = Color.CYAN

    print()
    print(f"{c_border}╭{'─' * (w - 2)}╮{Color.RESET}")
    title_line = f" ANTIGRAVITY MCP ORCHESTRATOR {c_v}v{version}{Color.RESET}"
    pad1 = inner - (30 + len(version))
    print(f"{c_border}│{Color.RESET} {c_title}●{Color.RESET}{title_line}{' ' * max(pad1, 1)}{c_border}│{Color.RESET}")

    sub_line = f" Model Context Protocol for Google Gemini & Antigravity IDE"
    pad2 = inner - len(sub_line)
    print(f"{c_border}│{Color.RESET}{c_sub}{sub_line}{Color.RESET}{' ' * max(pad2, 1)}{c_border}│{Color.RESET}")
    print(f"{c_border}╰{'─' * (w - 2)}╯{Color.RESET}")


def render_box(title: str, rows: List[tuple], border_color: str = Color.DARK_GRAY, width: Optional[int] = None) -> None:
    """
    Renders structured key-value card with rounded corners and consistent padding.
    """
    w = width or get_terminal_width()
    inner = w - 4

    print(f"{border_color}╭─ {Color.BOLD}{title}{Color.RESET} {border_color}{'─' * max(w - len(title) - 6, 2)}╮{Color.RESET}")

    max_key_len = max((len(k) for k, _ in rows if k), default=12)

    for k, v in rows:
        if k == "---":
            print(f"{border_color}├{'─' * (w - 2)}┤{Color.RESET}")
            continue
        if not k:
            # Full width value line
            pad = inner - len(strip_ansi(v))
            print(f"{border_color}│{Color.RESET} {v}{' ' * max(pad, 0)} {border_color}│{Color.RESET}")
        else:
            k_fmt = f"{Color.GRAY}{k.ljust(max_key_len)}{Color.RESET}"
            content = f" {k_fmt}  {v}"
            plain_len = 1 + max_key_len + 2 + len(strip_ansi(v))
            pad = inner - plain_len
            print(f"{border_color}│{Color.RESET}{content}{' ' * max(pad, 0)} {border_color}│{Color.RESET}")

    print(f"{border_color}╰{'─' * (w - 2)}╯{Color.RESET}")


def render_connection_guide(tunnel_url: str) -> None:
    """Displays Gemini connection card with clear, highlightable copy targets."""
    w = get_terminal_width()
    inner = w - 4

    print()
    print(f"{Color.GREEN}╭─ {Color.BOLD}GOOGLE GEMINI CONNECTED APPS READY{Color.RESET} {Color.GREEN}{'─' * max(w - 38, 2)}╮{Color.RESET}")

    lines = [
        f"{Color.GRAY}Copy and paste the SSE URL below into Gemini:{Color.RESET}",
        f"{Color.BOLD}{Color.CYAN}{tunnel_url}/sse{Color.RESET}",
        "",
        f"{Color.GRAY}Server Base:{Color.RESET}  {Color.WHITE}{tunnel_url}{Color.RESET}",
        f"{Color.GRAY}Status:{Color.RESET}       {Color.GREEN}● Active (Public Cloudflare Tunnel){Color.RESET}",
        f"{Color.GRAY}Transports:{Color.RESET}   SSE, Streamable HTTP POST, JSON-RPC 2.0"
    ]

    for line in lines:
        pad = inner - len(strip_ansi(line))
        print(f"{Color.GREEN}│{Color.RESET} {line}{' ' * max(pad, 0)} {Color.GREEN}│{Color.RESET}")

    print(f"{Color.GREEN}╰{'─' * (w - 2)}╯{Color.RESET}")
    print()


def strip_ansi(text: str) -> str:
    """Removes ANSI color codes to accurately calculate visual length."""
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)
