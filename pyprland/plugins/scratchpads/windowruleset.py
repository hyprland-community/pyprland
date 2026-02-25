"""WindowRuleSet builder for Hyprland windowrules."""

__all__ = ["WindowRuleSet"]

from collections.abc import Iterable

from ...common import SharedState
from ...models import VersionInfo


class WindowRuleSet:
    """Windowrule set builder."""

    def __init__(self, state: SharedState) -> None:
        self.state = state
        self._params: list[tuple[str, str]] = []
        self._class = ""
        self._name = "PyprScratchR"

    def set_class(self, value: str) -> None:
        """Set the windowrule matching class.

        Args:
            value: The class name
        """
        self._class = value

    def set_name(self, value: str) -> None:
        """Set the windowrule name.

        Args:
            value: The name
        """
        self._name = value

    def set(self, param: str, value: str) -> None:
        """Set a windowrule property.

        Args:
            param: The property name
            value: The property value
        """
        self._params.append((param, value))

    def _get_content(self) -> Iterable[str]:
        """Get the windowrule content."""
        if self.state.hyprland_version > VersionInfo(0, 47, 2):
            if self.state.hyprland_version < VersionInfo(0, 53, 0):
                for p in self._params:
                    yield f"windowrule {p[0]} {p[1]}, class: {self._class}"
            elif self._name:
                yield f"windowrule[{self._name}]:enable true"
                yield f"windowrule[{self._name}]:match:class {self._class}"
                for p in self._params:
                    yield f"windowrule[{self._name}]:{p[0]} {p[1]}"
            else:
                for p in self._params:
                    yield f"windowrule {p[0]} {p[1]}, match:class {self._class}"
        else:
            for p in self._params:
                yield f"windowrule {p[0]} {p[1]}, ^({self._class})$"

    def get_content(self) -> list[str]:
        """Get the windowrule content."""
        return list(self._get_content())
