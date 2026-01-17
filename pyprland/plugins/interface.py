"""Common plugin interface."""

import contextlib
from typing import Any

from ..adapters.backend import EnvironmentBackend
from ..common import Configuration, SharedState, get_logger
from ..models import ClientInfo


class Plugin:
    """Base class for any pyprland plugin."""

    aborted = False

    environments: list[str] = []
    " The supported environments for this plugin. Empty list means all environments. "

    backend: EnvironmentBackend
    " The environment backend "

    # Deprecated methods calling backend equivalent

    async def hyprctl_json(self, command: str) -> Any:  # noqa: ANN401
        """(Deprecated) Execute a hyprctl command and return the JSON result."""
        return await self.backend.execute_json(command)

    async def hyprctl(self, command: str | list[str], **kwargs: Any) -> bool:  # noqa: ANN401
        """(Deprecated) Execute a hyprctl command."""
        return await self.backend.execute(command, **kwargs)

    async def nirictl(self, command: str | list | dict, **kwargs: Any) -> bool:  # noqa: ANN401
        """(Deprecated) Execute a nirictl command."""
        return await self.backend.execute(command, **kwargs)

    async def nirictl_json(self, command: str) -> Any:  # noqa: ANN401
        """(Deprecated) Execute a nirictl command and return the JSON result."""
        return await self.backend.execute_json(command)

    async def notify(self, message: str, duration: int = 5000, color: str = "ff1010") -> None:
        """(Deprecated) Send a notification."""
        await self.backend.notify(message, duration, color)

    async def notify_info(self, message: str, duration: int = 5000) -> None:
        """(Deprecated) Send an info notification."""
        await self.backend.notify_info(message, duration)

    async def notify_error(self, message: str, duration: int = 5000) -> None:
        """(Deprecated) Send an error notification."""
        await self.backend.notify_error(message, duration)

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
        # Deprecated: use self.backend.* instead
        # ctrl = get_controls(self.log)
        # (
        #     self.hyprctl,
        #     self.hyprctl_json,  # pylint: disable=invalid-name
        #     self.notify,
        #     self.notify_info,
        #     self.notify_error,
        #     self.nirictl,
        #     self.nirictl_json,
        # ) = ctrl
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
        return await self.backend.get_clients(mapped, workspace, workspace_bl)
