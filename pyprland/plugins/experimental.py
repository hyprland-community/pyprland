"""Plugin template."""

from ..validation import ConfigItems
from .interface import Plugin


class Extension(Plugin):
    """Sample plugin template."""

    environments = ["hyprland"]

    # This plugin has no configuration options (template)
    config_schema = ConfigItems()
