" Common plugin interface "
from typing import Any

from ..common import get_logger
from ..ipc import getCtrlObjects


class Plugin:
    "Base plugin class, handles logger and config"

    def __init__(self, name: str):
        "create a new plugin `name` and the matching logger"
        self.name = name
        self.log = get_logger(name)
        self.hyprctl, self.hyprctlJSON, self.notify = getCtrlObjects(self.log)
        self.config: dict[str, Any] = {}

    async def init(self):
        "empty init function"

    async def exit(self):
        "empty exit function"

    async def load_config(self, config: dict[str, Any]):
        "Loads the configuration section from the passed `config`"
        try:
            self.config = config[self.name]
        except KeyError:
            self.config = {}
