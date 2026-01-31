"""Plugin template."""

from typing import ClassVar

from .interface import Plugin


class Extension(Plugin):
    """Sample plugin template."""

    environments: ClassVar[list[str]] = ["hyprland"]
