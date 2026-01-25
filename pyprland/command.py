"""Pyprland - an Hyprland companion app (cli client & daemon)."""

import asyncio
import json
import os
import sys

from . import constants as pyprland_constants
from .client import run_client
from .common import get_logger, init_logger
from .constants import CONTROL
from .ipc import init as ipc_init
from .manager import Pyprland
from .models import PyprError
from .pypr_daemon import run_daemon

__all__: list[str] = ["Pyprland", "main"]


def use_param(txt: str) -> str:
    """Check if parameter `txt` is in sys.argv.

    if found, removes it from sys.argv & returns the argument value

    Args:
        txt: Parameter name to look for
    """
    v = ""
    if txt in sys.argv:
        i = sys.argv.index(txt)
        v = sys.argv[i + 1]
        del sys.argv[i : i + 2]
    return v


def main() -> None:
    """Run the command."""
    debug_flag = use_param("--debug")
    if debug_flag:
        init_logger(filename=debug_flag, force_debug=True)
    else:
        init_logger()
    ipc_init()
    log = get_logger("startup")

    config_override = use_param("--config")
    if config_override:
        pyprland_constants.CONFIG_FILE = config_override

    invoke_daemon = len(sys.argv) <= 1
    if invoke_daemon and os.path.exists(CONTROL):
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
            if invoke_daemon and os.path.exists(CONTROL):
                os.unlink(CONTROL)


if __name__ == "__main__":
    main()
