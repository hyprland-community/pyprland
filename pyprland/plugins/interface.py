"""Common plugin interface."""

import contextlib
from collections.abc import Callable
from typing import Any, cast

from ..common import Configuration, get_logger
from ..ipc import get_controls
from ..types import ClientInfo


class Plugin:
    """Base class for any pyprland plugin."""

    aborted = False

    hyprctl_json: Callable
    " `pyprland.ipc.hyprctl_json` using the plugin's logger "

    hyprctl: Callable
    " `pyprland.ipc.hyprctl` using the plugin's logger "

    notify: Callable
    " `pyprland.ipc.notify` using the plugin's logger "

    notify_info: Callable
    " `pyprland.ipc.notify_info` using the plugin's logger "

    notify_error: Callable
    " `pyprland.ipc.notify_error` using the plugin's logger "

    config: Configuration
    " This plugin configuration section as a `dict` object "

    def __init__(self, name: str) -> None:
        """Create a new plugin `name` and the matching logger."""
        self.name = name
        """ the plugin name """
        self.log = get_logger(name)
        """ the logger to use for this plugin """
        ctrl = get_controls(self.log)
        (
            self.hyprctl,
            self.hyprctl_json,  # pylint: disable=invalid-name
            self.notify,
            self.notify_info,
            self.notify_error,
        ) = ctrl
        self.config = Configuration({}, logger=self.log)

    # Functions to override

    async def init(self) -> None:
        """Initialize the plugin.

        Note that the `config` attribute isn't ready yet when this is called.
        """

    async def on_reload(self) -> None:
        """Add the code which requires the `config` attribute here.

        This is called on *init* and *reload*
        """

    async def exit(self) -> None:
        """Empty exit function."""

    # Generic implementations

    async def load_config(self, config: dict[str, Any]) -> None:
        """Load the configuration section from the passed `config`."""
        self.config.clear()
        with contextlib.suppress(KeyError):
            self.config.update(config[self.name])

    async def get_clients(
        self,
        mapped: bool = True,
        workspace: None | str = None,
        workspace_bl: str | None = None,
    ) -> list[ClientInfo]:
        """Return the client list, optionally returns only mapped clients or from a given workspace."""
        return [
            client
            for client in cast("list[ClientInfo]", await self.hyprctl_json("clients"))
            if (not mapped or client["mapped"])
            and (workspace is None or cast("str", client["workspace"]["name"]) == workspace)
            and (workspace_bl is None or cast("str", client["workspace"]["name"]) != workspace_bl)
        ]
