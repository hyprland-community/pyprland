"""Menu engine adapter."""

import asyncio
import subprocess
from collections.abc import Iterable
from logging import Logger
from typing import TYPE_CHECKING, ClassVar

from ..common import apply_variables, get_logger
from ..models import PyprError, ReloadReason
from ..validation import ConfigField, ConfigItems

if TYPE_CHECKING:
    from ..config import Configuration

__all__ = ["MenuEngine", "MenuMixin"]

menu_logger = get_logger("menus adapter")


class MenuEngine:
    """Menu backend interface."""

    proc_name: str
    " process name for this engine "
    proc_extra_parameters: str = ""
    " process parameters to use for this engine "
    proc_detect_parameters: ClassVar[list[str]] = ["--help"]
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
            subprocess.call([cls.proc_name, *cls.proc_detect_parameters], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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


def _menu(proc: str, params: str) -> type[MenuEngine]:
    """Create a menu engine class.

    Args:
        proc: process name for this engine
        params: default parameters to pass to the process

    Returns:
        A MenuEngine subclass configured for the specified menu program
    """
    return type(
        f"{proc.title()}Menu",
        (MenuEngine,),
        {"proc_name": proc, "proc_extra_parameters": params, "__doc__": f"A {proc} based menu."},
    )


TofiMenu = _menu("tofi", "--prompt-text '[prompt]'")
RofiMenu = _menu("rofi", "-dmenu -i -p '[prompt]'")
WofiMenu = _menu("wofi", "-dmenu -i -p '[prompt]'")
DmenuMenu = _menu("dmenu", "-i")
BemenuMenu = _menu("bemenu", "-c")
FuzzelMenu = _menu("fuzzel", "--match-mode=fuzzy -d -p '[prompt]'")
WalkerMenu = _menu("walker", "-d -k -p '[prompt]'")
AnyrunMenu = _menu("anyrun", "--plugins libstdin.so --show-results-immediately true")

every_menu_engine = [FuzzelMenu, TofiMenu, RofiMenu, WofiMenu, BemenuMenu, DmenuMenu, AnyrunMenu, WalkerMenu]

MENU_ENGINE_CHOICES: list[str] = [engine.proc_name for engine in every_menu_engine]
"""List of available menu engine names, derived from every_menu_engine."""


async def init(force_engine: str | None = None, extra_parameters: str = "") -> MenuEngine:
    """Initialize the module.

    Args:
        force_engine: Name of the engine to force use of
        extra_parameters: Extra parameters to pass to the engine
    """
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

    menu_config_schema = ConfigItems(
        ConfigField(
            "engine",
            str,
            description="Menu engine to use",
            choices=MENU_ENGINE_CHOICES,
            category="menu",
        ),
        ConfigField(
            "parameters",
            str,
            description="Extra parameters for the menu engine command",
            category="menu",
        ),
    )
    """Schema for menu configuration fields. Plugins using MenuMixin should include this in their config_schema."""

    _menu_configured = False
    menu: MenuEngine
    """ provided `MenuEngine` """
    config: "Configuration"
    " used by the mixin but provided by `pyprland.plugins.interface.Plugin` "
    log: Logger

    " used by the mixin but provided by `pyprland.plugins.interface.Plugin` "

    async def ensure_menu_configured(self) -> None:
        """If not configured, init the menu system."""
        if not self._menu_configured:
            self.menu = await init(self.config.get_str("engine") or None, self.config.get_str("parameters"))
            self.log.info("Using %s engine", self.menu.proc_name)
            self._menu_configured = True

    async def on_reload(self, reason: ReloadReason = ReloadReason.RELOAD) -> None:
        """Reset the configuration status."""
        _ = reason  # unused
        self._menu_configured = False
