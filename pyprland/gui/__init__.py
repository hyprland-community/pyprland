"""Web-based configuration editor for pyprland.

Provides a local web server with a Vue.js frontend for viewing and editing
the pyprland configuration file. Uses plugin schema metadata for type-aware
form generation.

Usage:
    pypr-gui              # Start server and open browser
    pypr-gui -s           # Print URL (start server in background if needed)
    pypr-gui -w           # Open browser (explicit, same as default)
    pypr-gui --no-browser # Start server without opening browser
    pypr-gui --port N     # Use a specific port
"""

from __future__ import annotations

import asyncio
import atexit
import json
import logging
import os
import signal
import socket
import sys
import time
import webbrowser
from pathlib import Path

from .server import create_app

__all__ = ["main"]

# Default port (fixed so the URL is predictable across invocations)
DEFAULT_PORT = 18099

# Lock file location (next to the pyprland daemon socket)
_xdg_runtime = Path(os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/pypr-{os.getuid()}")  # noqa: S108
LOCK_FILE = _xdg_runtime / "pypr" / "gui.lock"

# How long to wait when probing an existing instance
_PROBE_TIMEOUT = 2.0

# How long the parent waits for the daemonized server to become ready
_DAEMON_STARTUP_TIMEOUT = 5.0
_DAEMON_POLL_INTERVAL = 0.1


def _find_free_port() -> int:
    """Find an available TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _write_lock(port: int) -> None:
    """Write the lock file with our port and PID."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.write_text(json.dumps({"port": port, "pid": os.getpid()}), encoding="utf-8")


def _remove_lock() -> None:
    """Remove the lock file if it belongs to us."""
    try:
        if LOCK_FILE.exists():
            data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
            if data.get("pid") == os.getpid():
                LOCK_FILE.unlink()
    except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        logging.getLogger(__name__).debug("Failed to remove lock file", exc_info=True)


def _check_existing_instance() -> int | None:
    """Check if another gui instance is already running.

    Returns:
        The port number if a live instance is found, None otherwise.
    """
    if not LOCK_FILE.exists():
        return None

    try:
        data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        port = data["port"]
        pid = data.get("pid")

        # Check if the process is alive
        if pid:
            try:
                os.kill(pid, 0)
            except OSError:
                # Process is dead - stale lock
                LOCK_FILE.unlink(missing_ok=True)
                return None

        # Verify the server is actually responding
        with socket.create_connection(("127.0.0.1", port), timeout=_PROBE_TIMEOUT):
            return port

    except (json.JSONDecodeError, KeyError, OSError):
        # Corrupt lock file or server not responding
        LOCK_FILE.unlink(missing_ok=True)
        return None


def _wait_for_server(port: int) -> bool:
    """Poll until the server is accepting connections.

    Returns:
        True if the server became ready, False on timeout.
    """
    deadline = time.monotonic() + _DAEMON_STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=_PROBE_TIMEOUT):
                return True
        except OSError:
            time.sleep(_DAEMON_POLL_INTERVAL)
    return False


def _start_server(port: int) -> None:
    """Start the aiohttp server (blocks until shutdown)."""
    from aiohttp import web  # noqa: PLC0415

    _write_lock(port)
    atexit.register(_remove_lock)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    app = create_app()
    web.run_app(app, host="127.0.0.1", port=port, print=lambda _: None)


def _daemonize_server(port: int) -> bool:
    """Fork and start the server in a background process.

    The parent returns True once the server is ready, or False on timeout.
    The child never returns (it runs the server until killed).
    """
    pid = os.fork()
    if pid > 0:
        # Parent: wait for the child to be ready, then return
        return _wait_for_server(port)

    # Child: detach from the terminal and run the server
    os.setsid()

    # Close inherited stdio so the parent's terminal is released
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, 0)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    os.close(devnull)

    _start_server(port)
    sys.exit(0)  # unreachable, but explicit


def main() -> None:
    """Entry point for pypr-gui."""
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(description="Pyprland configuration editor")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to listen on (default: {DEFAULT_PORT})")
    parser.add_argument("-w", action="store_true", help="Open browser")
    parser.add_argument("-s", action="store_true", help="Print URL (start server in background if needed)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    port = args.port
    open_browser = (not args.no_browser and not args.s) or args.w

    # Check for existing instance
    existing_port = _check_existing_instance()

    if existing_port:
        url = f"http://127.0.0.1:{existing_port}"
        if args.s:
            print(url)
        else:
            print(f"pypr-gui is already running at {url}")
        if open_browser:
            webbrowser.open(url)
        sys.exit(0)

    url = f"http://127.0.0.1:{port}"

    if args.s:
        # Start server in background, print URL, exit
        if _daemonize_server(port):
            print(url)
        else:
            print(f"Failed to start pypr-gui on port {port}", file=sys.stderr)
            sys.exit(1)
        if args.w:
            webbrowser.open(url)
        sys.exit(0)

    # Foreground mode: start server and optionally open browser
    print(f"Starting pypr-gui at {url}")
    if open_browser:
        loop = asyncio.new_event_loop()
        loop.call_later(0.5, webbrowser.open, url)

    _start_server(port)
