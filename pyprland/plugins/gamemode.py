"""Gamemode plugin - toggle performance mode for gaming.

Provides manual toggle and automatic detection of game windows.
When game mode is enabled, disables animations, blur, shadows, gaps,
and rounding for maximum performance.
"""

import fnmatch

from ..models import Environment, ReloadReason
from ..validation import ConfigField, ConfigItems
from .interface import Plugin

# Minimum number of parts expected in openwindow event params
# Format: "address,workspace,class,title" - we need at least address, workspace, class
_MIN_OPENWINDOW_PARTS = 3


class Extension(Plugin, environments=[Environment.HYPRLAND]):
    """Toggle game mode for improved performance.

    When enabled, disables animations, blur, shadows, gaps, and rounding
    for maximum performance. When disabled, reloads the hyprland config
    to restore original settings.

    Supports automatic detection of game windows based on window class
    patterns (e.g., Steam games with class "steam_app_*").
    """

    config_schema = ConfigItems(
        ConfigField("border_size", int, default=1, description="Border size when game mode is enabled", category="basic"),
        ConfigField("notify", bool, default=True, description="Show notification when toggling", category="basic"),
        ConfigField(
            "auto", bool, default=True, description="Automatically enable game mode when matching windows are detected", category="basic"
        ),
        ConfigField(
            "patterns",
            list,
            default=["steam_app_*"],
            description="Glob patterns to match window class for auto mode",
            category="basic",
        ),
    )

    _enabled: bool = False
    _game_windows: set[str]

    def __init__(self, name: str) -> None:
        """Initialize plugin state."""
        super().__init__(name)
        self._game_windows = set()

    def _matches_pattern(self, window_class: str) -> bool:
        """Check if window class matches any configured pattern.

        Args:
            window_class: The window class to check

        Returns:
            True if the class matches any pattern in the configured patterns list
        """
        patterns = self.get_config_list("patterns")
        return any(fnmatch.fnmatch(window_class, pattern) for pattern in patterns)

    async def _enable_gamemode(self, notify: bool = True) -> None:
        """Enable game mode (disable visual effects).

        Args:
            notify: Whether to show notification (default: True)
        """
        if self._enabled:
            return

        border_size = self.get_config_int("border_size")
        await self.backend.execute(
            [
                "animations:enabled 0",
                "decoration:shadow:enabled 0",
                "decoration:blur:enabled 0",
                "decoration:fullscreen_opacity 1",
                "general:gaps_in 0",
                "general:gaps_out 0",
                f"general:border_size {border_size}",
                "decoration:rounding 0",
            ],
            base_command="keyword",
        )
        self._enabled = True

        if notify and self.get_config_bool("notify"):
            await self.backend.notify_info("Gamemode [ON]")

    async def _disable_gamemode(self, notify: bool = True) -> None:
        """Disable game mode (reload config to restore).

        Args:
            notify: Whether to show notification (default: True)
        """
        if not self._enabled:
            return

        await self.backend.execute("config-only", base_command="reload")
        self._enabled = False

        if notify and self.get_config_bool("notify"):
            await self.backend.notify_info("Gamemode [OFF]")

    async def on_reload(self, reason: ReloadReason = ReloadReason.RELOAD) -> None:
        """Initialize state by checking current animations setting."""
        if reason != ReloadReason.INIT:
            return

        # Check current animations state to determine if game mode is already on
        option = await self.backend.execute_json("getoption animations:enabled")
        self._enabled = option.get("int", 1) == 0

        # Scan existing clients for game windows if auto is enabled
        if self.get_config_bool("auto"):
            clients = await self.backend.get_clients()
            for client in clients:
                window_class = str(client.get("class", ""))
                if self._matches_pattern(window_class):
                    # Address comes with 0x prefix, store without it for consistency with events
                    addr = str(client.get("address", "")).replace("0x", "")
                    if addr:
                        self._game_windows.add(addr)

            # Enable if games are already running and game mode is not on
            if self._game_windows and not self._enabled:
                await self._enable_gamemode()

    async def run_gamemode(self) -> None:
        """Toggle game mode (disables animations, blur, shadows, gaps, rounding)."""
        if self._enabled:
            await self._disable_gamemode()
        else:
            await self._enable_gamemode()

    async def event_openwindow(self, params: str) -> None:
        """Handle window open - check for game windows.

        Args:
            params: Format "address,workspace,class,title"
        """
        if not self.get_config_bool("auto"):
            return

        # Parse params: "address,workspace,class,title"
        parts = params.split(",", 3)
        if len(parts) < _MIN_OPENWINDOW_PARTS:
            return

        addr, _, window_class = parts[0], parts[1], parts[2]

        if self._matches_pattern(window_class):
            self._game_windows.add(addr)
            await self._enable_gamemode()

    async def event_closewindow(self, addr: str) -> None:
        """Handle window close - disable game mode if no games left.

        Args:
            addr: Window address as hex string (without 0x prefix)
        """
        if addr not in self._game_windows:
            return

        self._game_windows.discard(addr)

        if not self._game_windows:
            await self._disable_gamemode()
