" Not a real Plugin - provides some core features and some caching of commonly requested structures "
from .interface import Plugin


class Extension(Plugin):
    "Internal built-in plugin allowing caching states and implementing special commands"

    def set_commands(self, **cmd_map):
        "Set some commands, made available as run_`name` methods"
        for name, fn in cmd_map.items():
            setattr(self, f"run_{name}", fn)
