from typing import Any
from ..common import get_logger


class Plugin:
    def __init__(self, name: str):
        self.name = name
        self.log = get_logger(name)

    async def init(self):
        pass

    async def exit(self):
        return

    async def load_config(self, config: dict[str, Any]):
        try:
            self.config = config[self.name]
        except KeyError:
            self.config = {}
