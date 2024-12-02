"""Menu engine adapter."""

import asyncio
import subprocess
from collections.abc import Iterable
from logging import Logger

from ..common import apply_variables, get_logger
from ..types import PyprError

__all__ = ["MenuEngine", "MenuMixin"]

menu_logger = get_logger("menus adapter")


class MenuEngine:
    """Menu backend interface."""

    proc_name: str
    " process name for this engine "
    proc_extra_parameters: str = ""
    " process parameters to use for this engine "
    proc_detect_parameters: list[str] = ["--help"]
    " process parameters used to check if the engine can run "

    def __init__(self, extra_parameters: str) -> None:
        """Initialize the engine with extra parameters.

        Args:
            extra_parameters: extra parameters to pass to the program
        """
        if extra_parameters:
            self.proc_extra_parameters = extra_parameters

    @classmethod
    def is_available(cls) -> bool:
        """Check engine availability."""
        try:
            subprocess.call([cls.proc_name, *cls.proc_detect_parameters])
        except FileNotFoundError:
            return False
        return True

    async def run(self, choices: Iterable[str], prompt: str = "") -> str:
        """Run the engine and get the response for the proposed `choices`.

        Args:
            choices: options to chose from
            prompt: prompt replacement variable (passed in `apply_variables`)

        Returns:
            The choice which have been selected by the user, or an empty string
        """
        menu_text = "\n".join(choices)
        if not menu_text.strip():
            return ""
        command = apply_variables(
            f"{self.proc_name} {self.proc_extra_parameters}",
            {"prompt": f"{prompt}:  "} if prompt else {"prompt": ""},
        )
        menu_logger.debug(command)
        proc = await asyncio.create_subprocess_shell(
            command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
        )
        assert proc.stdin
        assert proc.stdout

        proc.stdin.write(menu_text.encode())
        # flush program execution
        await proc.stdin.drain()
        proc.stdin.close()
        await proc.wait()

        return (await proc.stdout.read()).decode().strip()


class TofiMenu(MenuEngine):
    """A tofi based menu."""

    proc_name = "tofi"
    proc_extra_parameters: str = "--prompt-text '[prompt]'"


class RofiMenu(MenuEngine):
    """A rofi based menu."""

    proc_name = "rofi"
    proc_extra_parameters = "-dmenu -matching fuzzy -i -p '[prompt]'"


class WofiMenu(MenuEngine):
    """A wofi based menu."""

    proc_name = "wofi"
    proc_extra_parameters = "-dmenu -i -p '[prompt]'"


class DmenuMenu(MenuEngine):
    """A dmenu based menu."""

    proc_name = "dmenu"
    proc_extra_parameters = "-i"


class BemenuMenu(MenuEngine):
    """A bemenu based menu."""

    proc_name = "bemenu"
    proc_extra_parameters = "-c"


class WalkerMenu(MenuEngine):
    """A walker based menu."""

    proc_name = "walker"
    proc_extra_parameters = "-d -k -p '[prompt]'"


class AnyrunMenu(MenuEngine):
    """A bemenu based menu."""

    proc_name = "anyrun"
    proc_extra_parameters = "--plugins libstdin.so --show-results-immediately true"


every_menu_engine = [WalkerMenu, TofiMenu, RofiMenu, WofiMenu, BemenuMenu, DmenuMenu, AnyrunMenu]


async def init(force_engine: str | None = None, extra_parameters: str = "") -> MenuEngine:
    """Initialize the module."""
    try:
        engines = [next(e for e in every_menu_engine if e.proc_name == force_engine)] if force_engine else every_menu_engine
    except StopIteration:
        engines = []

    if force_engine and engines:
        return engines[0](extra_parameters)

    # detect engine
    for engine in engines:
        if engine.is_available():
            return engine(extra_parameters)

    # fallback if not found but forced
    if force_engine:
        # Attempt to use the user-supplied command
        me = MenuEngine(extra_parameters)
        me.proc_name = force_engine
        return me

    msg = "No engine found"
    raise PyprError(msg)


class MenuMixin:
    """An extension mixin supporting 'engine' and 'parameters' config options to show a menu."""

    _menu_configured = False
    menu: MenuEngine
    """ provided `MenuEngine` """
    config: dict
    " used by the mixin but provided by `pyprland.plugins.interface.Plugin` "
    log: Logger
    " used by the mixin but provided by `pyprland.plugins.interface.Plugin` "

    async def ensure_menu_configured(self) -> None:
        """If not configured, init the menu system."""
        if not self._menu_configured:
            self.menu = await init(self.config.get("engine"), self.config.get("parameters", ""))
            self.log.info("Using %s engine", self.menu.proc_name)
            self._menu_configured = True

    async def on_reload(self) -> None:
        """Reset the configuration status."""
        self._menu_configured = False
