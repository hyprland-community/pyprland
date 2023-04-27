from typing import Any


class Plugin:
    def __init__(self, name: str):
        self.name = name

    async def init(self):
        pass

    async def exit(self):
        return

    async def load_config(self, config: dict[str, Any]):
        try:
            self.config = config[self.name]
        except KeyError:
            self.config = {}
