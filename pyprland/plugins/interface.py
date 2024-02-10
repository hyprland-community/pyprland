" Common plugin interface "
from typing import Any, cast, Callable

from ..common import get_logger
from ..ipc import getCtrlObjects


class Plugin:
    """Base class for any pyprland plugin"""

    hyprctlJSON: Callable
    " `pyprland.ipc.hyprctlJSON` using the pluggin's logger "

    hyprctl: Callable
    " `pyprland.ipc.hyprctl` using the pluggin's logger "

    notify: Callable
    " `pyprland.ipc.notify` using the pluggin's logger "

    notify_info: Callable
    " `pyprland.ipc.notify_info` using the pluggin's logger "

    notify_error: Callable
    " `pyprland.ipc.notify_error` using the pluggin's logger "

    config: dict[str, Any]
    " This plugin configuration section as a dict object "

    def __init__(self, name: str):
        "create a new plugin `name` and the matching logger"
        self.name = name
        """ the plugin name """
        self.log = get_logger(name)
        """ the logger to use for this plugin """
        ctrl = getCtrlObjects(self.log)
        (
            self.hyprctl,
            self.hyprctlJSON,  # pylint: disable=invalid-name
            self.notify,
            self.notify_info,
            self.notify_error,
        ) = ctrl
        self.config = {}

    # Functions to override

    async def init(self):
        """
        This should contain the code you would normally add to `__init__`.
        Note that the `config` attribute isn't ready yet when this is called.
        """

    async def on_reload(self):
        """
        Add the code which requires the `config` attribute here.
        This is called on *init* and *reload*
        """

    async def exit(self):
        "empty exit function"

    # Generic implementations

    async def load_config(self, config: dict[str, Any]):
        "Loads the configuration section from the passed `config`"
        self.config.clear()
        try:
            self.config.update(config[self.name])
        except KeyError:
            self.config = {}

    async def get_clients(self, mapped=True, workspace=None, workspace_bl=None):
        "Return the client list, optionally returns only mapped clients or from a given workspace"
        return [
            client
            for client in cast(list[dict[str, Any]], await self.hyprctlJSON("clients"))
            if (not mapped or client["mapped"])
            and (
                workspace is None or cast(str, client["workspace"]["name"]) == workspace
            )
            and (
                workspace_bl is None
                or cast(str, client["workspace"]["name"]) != workspace_bl
            )
        ]
