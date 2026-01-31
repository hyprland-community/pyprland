"""Pyprland - an Hyprland companion app (cli client & daemon)."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Literal, overload

from . import constants as pyprland_constants
from .client import run_client
from .common import get_logger, init_logger
from .constants import CONTROL
from .ipc import init as ipc_init
from .manager import Pyprland
from .models import PyprError
from .pypr_daemon import run_daemon

__all__: list[str] = ["Pyprland", "main"]


@overload
def use_param(txt: str, optional_value: Literal[False] = ...) -> str: ...


@overload
def use_param(txt: str, optional_value: Literal[True]) -> str | bool: ...


def use_param(txt: str, optional_value: bool = False) -> str | bool:
    """Check if parameter `txt` is in sys.argv.

    If found, removes it from sys.argv & returns the argument value.
    If optional_value is True, the parameter value is optional.

    Args:
        txt: Parameter name to look for
        optional_value: If True, value after parameter is optional

    Returns:
        - "" if parameter not present
        - True if parameter present but no value (only when optional_value=True)
        - The value string if parameter present with value
    """
    if txt not in sys.argv:
        return ""
    i = sys.argv.index(txt)
    # Check if there's a next arg and it's not a flag
    if optional_value and (i + 1 >= len(sys.argv) or sys.argv[i + 1].startswith("-")):
        del sys.argv[i]
        return True
    v = sys.argv[i + 1]
    del sys.argv[i : i + 2]
    return v


def main() -> None:
    """Run the command."""
    debug_flag = use_param("--debug", optional_value=True)
    if debug_flag:
        filename = debug_flag if isinstance(debug_flag, str) else None
        init_logger(filename=filename, force_debug=True)
    else:
        init_logger()
    ipc_init()
    log = get_logger("startup")

    config_override = use_param("--config")
    if config_override:
        pyprland_constants.CONFIG_FILE = config_override

    invoke_daemon = len(sys.argv) <= 1
    if invoke_daemon and Path(CONTROL).exists():
        log.critical(
            """%s exists,
is pypr already running ?
If that's not the case, delete this file and run again.""",
            CONTROL,
        )
    else:
        try:
            asyncio.run(run_daemon() if invoke_daemon else run_client())
        except KeyboardInterrupt:
            pass
        except PyprError:
            log.critical("Command failed.")
        except json.decoder.JSONDecodeError as e:
            log.critical("Invalid JSON syntax in the config file: %s", e.args[0])
        except Exception:  # pylint: disable=W0718
            log.critical("Unhandled exception:", exc_info=True)
        finally:
            if invoke_daemon and Path(CONTROL).exists():
                Path(CONTROL).unlink()


if __name__ == "__main__":
    main()
