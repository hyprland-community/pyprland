"""Common plugin interface."""

import contextlib
from collections.abc import Callable
from typing import Any, cast

from ..common import Configuration, SharedState, get_logger
from ..ipc import get_controls
from ..models import ClientInfo


class Plugin:
    """Base class for any pyprland plugin."""

    aborted = False

    environments: list[str] = []
    " The supported environments for this plugin. Empty list means all environments. "

    hyprctl_json: Callable
    " `pyprland.ipc.hyprctl_json` using the plugin's logger "

    hyprctl: Callable
    " `pyprland.ipc.hyprctl` using the plugin's logger "

    nirictl: Callable
    " `pyprland.ipc.nirictl` using the plugin's logger "

    nirictl_json: Callable
    " `pyprland.ipc.nirictl_json` using the plugin's logger "

    notify: Callable
    " `pyprland.ipc.notify` using the plugin's logger "

    notify_info: Callable
    " `pyprland.ipc.notify_info` using the plugin's logger "

    notify_error: Callable
    " `pyprland.ipc.notify_error` using the plugin's logger "

    config: Configuration
    " This plugin configuration section as a `dict` object "

    state: SharedState
    " The shared state object "

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
            self.nirictl,
            self.nirictl_json,
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
        """Return the client list, optionally returns only mapped clients or from a given workspace.

        Args:
            mapped: Filter for mapped clients
            workspace: Filter for specific workspace name
            workspace_bl: Filter to blacklist a specific workspace name
        """
        if self.state.environment == "niri":
            return [
                self._map_niri_client(client)
                for client in cast("list[dict]", await self.nirictl_json("windows"))
                if (not mapped or client.get("is_mapped", True))
                and (workspace is None or str(client.get("workspace_id")) == workspace)
                and (workspace_bl is None or str(client.get("workspace_id")) != workspace_bl)
            ]
        return [
            client
            for client in cast("list[ClientInfo]", await self.hyprctl_json("clients"))
            if (not mapped or client["mapped"])
            and (workspace is None or cast("str", client["workspace"]["name"]) == workspace)
            and (workspace_bl is None or cast("str", client["workspace"]["name"]) != workspace_bl)
        ]

    def _map_niri_client(self, niri_client: dict[str, Any]) -> ClientInfo:
        """Helper to map Niri window dict to ClientInfo TypedDict."""
        return cast(
            "ClientInfo",
            {
                "address": str(niri_client.get("id")),
                "class": niri_client.get("app_id"),
                "title": niri_client.get("title"),
                "workspace": {"name": str(niri_client.get("workspace_id"))},
                "pid": -1,
                "mapped": niri_client.get("is_mapped", True),
                "hidden": False,
                "at": (0, 0),
                "size": (0, 0),
                "floating": False,
                "monitor": -1,
                "initialClass": niri_client.get("app_id"),
                "initialTitle": niri_client.get("title"),
                "xwayland": False,
                "pinned": False,
                "fullscreen": False,
                "fullscreenMode": 0,
                "fakeFullscreen": False,
                "grouped": [],
                "swallowing": "",
                "focusHistoryID": 0,
            },
        )
