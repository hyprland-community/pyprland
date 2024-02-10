" Common plugin interface "
from typing import Any, cast

from ..common import get_logger
from ..ipc import getCtrlObjects


class Plugin:
    "Base plugin class, handles logger and config"

    def __init__(self, name: str):
        "create a new plugin `name` and the matching logger"
        self.name = name
        self.log = get_logger(name)
        ctrl = getCtrlObjects(self.log)
        (
            self.hyprctl,
            self.hyprctlJSON,  # pylint: disable=invalid-name
            self.notify,
            self.notify_info,
            self.notify_error,
        ) = ctrl
        self.config: dict[str, Any] = {}

    # Functions to override

    async def init(self):
        "empty init function"

    async def on_reload(self):
        "empty reload function"

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
