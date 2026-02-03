"""Plugin template."""

from ..models import Environment
from .interface import Plugin


class Extension(Plugin, environments=[Environment.HYPRLAND]):
    """Sample plugin template."""
