"""Plugin template."""

from typing import ClassVar

from ..models import Environment
from .interface import Plugin


class Extension(Plugin):
    """Sample plugin template."""

    environments: ClassVar[list[Environment]] = [Environment.HYPRLAND]
