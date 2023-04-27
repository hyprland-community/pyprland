from .interface import Plugin

from ..ipc import hyprctlJSON, hyprctl, get_workspaces


class Experimental(Plugin):
    pass


Exported = Experimental
