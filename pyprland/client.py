"""Client-side functions for pyprland CLI."""

import asyncio
import os
import sys

from . import constants as pyprland_constants
from .common import run_interactive_program
from .manager import Pyprland
from .models import ExitCode, ResponsePrefix
from .validate_cli import run_validate

__all__ = ["run_client"]


async def run_client() -> None:
    """Run the client (CLI)."""
    manager = Pyprland()

    if sys.argv[1] == "edit":
        editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "vi"))
        filename = os.path.expanduser(pyprland_constants.CONFIG_FILE)
        run_interactive_program(f'{editor} "{filename}"')
        sys.argv[1] = "reload"

    elif sys.argv[1] == "validate":
        # Validate doesn't require daemon - run locally and exit
        run_validate()
        return

    elif sys.argv[1] in {"--help", "-h"}:
        sys.argv[1] = "help"

    try:
        reader, writer = await asyncio.open_unix_connection(pyprland_constants.CONTROL)
    except (ConnectionRefusedError, FileNotFoundError):
        manager.log.critical(
            "Cannot connect to pyprland daemon at %s.\nIs the daemon running? Start it with: pypr (no arguments)",
            pyprland_constants.CONTROL,
        )
        await manager.backend.notify_error("Pypr can't connect. Is daemon running?")
        sys.exit(ExitCode.CONNECTION_ERROR)

    args = sys.argv[1:]
    args[0] = args[0].replace("-", "_")
    writer.write((" ".join(args) + "\n").encode())
    writer.write_eof()
    await writer.drain()
    return_value = (await reader.read()).decode("utf-8")
    writer.close()
    await writer.wait_closed()

    # Parse response and set exit code
    if return_value.startswith(f"{ResponsePrefix.ERROR}:"):
        # Extract error message (skip "ERROR: " prefix)
        error_msg = return_value[len(ResponsePrefix.ERROR) + 2 :].strip()
        print(f"Error: {error_msg}", file=sys.stderr)
        sys.exit(ExitCode.COMMAND_ERROR)
    elif return_value.startswith(f"{ResponsePrefix.OK}"):
        # Command succeeded, check for additional output after OK
        remaining = return_value[len(ResponsePrefix.OK) :].strip()
        if remaining:
            print(remaining)
        sys.exit(ExitCode.SUCCESS)
    else:
        # Legacy response (version, help, dumpjson) - print as-is
        print(return_value.rstrip())
        sys.exit(ExitCode.SUCCESS)
