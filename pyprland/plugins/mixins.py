"""Reusable mixins for common plugin functionality.

MonitorTrackingMixin:
    Automatically tracks monitor add/remove events, maintaining a list
    of active monitors. Works with both regular plugins (self.monitors)
    and core plugins (self.state.monitors).
"""

from logging import Logger
from typing import cast


class MonitorListDescriptor:
    """Descriptor that resolves monitor list location at runtime.

    Priority order:
    1. self.monitors (instance attribute) - for regular plugins
    2. self.state.monitors - for core plugins storing in SharedState

    This allows plugins to choose where to store monitors:
    - Regular plugins: set self.monitors = [...] in init()
    - Core plugins: use self.state.monitors (SharedState)
    """

    def __get__(self, obj: object, _objtype: type | None = None) -> list[str]:
        """Get the monitor list from the appropriate location."""
        if obj is None:
            return []
        # Check for instance attribute 'monitors' first (not class attribute)
        if "monitors" in obj.__dict__:
            return cast("list[str]", obj.__dict__["monitors"])
        # Fall back to state.monitors for core plugins
        if hasattr(obj, "state") and hasattr(obj.state, "monitors"):
            return cast("list[str]", obj.state.monitors)
        return []

    def __set__(self, obj: object, value: list[str]) -> None:
        """Set the monitor list in the appropriate location."""
        # If monitors is already an instance attribute, update it
        if "monitors" in obj.__dict__:
            obj.__dict__["monitors"] = value
        # Otherwise, use state.monitors if available
        elif hasattr(obj, "state") and hasattr(obj.state, "monitors"):
            obj.state.monitors = value
        else:
            obj.__dict__["monitors"] = value


class MonitorTrackingMixin:
    """Mixin for plugins that need to track monitor add/remove events.

    This mixin automatically detects where to store the monitor list:
    - If self.state.monitors exists (core plugins), uses that
    - Otherwise uses self.monitors (regular plugins)

    Example usage for regular plugins:
        class Extension(MonitorTrackingMixin, Plugin):
            monitors: list[str] = []

            async def init(self):
                self.monitors = [m["name"] for m in await self.backend.get_monitors()]

    Example usage for core plugins (storing in SharedState):
        class HyprlandStateMixin(MonitorTrackingMixin):
            # self.state.monitors is used automatically
            pass
    """

    # These attributes are provided by the Plugin class
    log: Logger

    # Descriptor that resolves to the correct monitor list
    _monitors = MonitorListDescriptor()

    async def event_monitoradded(self, name: str) -> None:
        """Track monitor addition.

        Args:
            name: The monitor name
        """
        self._monitors.append(name)

    async def event_monitorremoved(self, name: str) -> None:
        """Track monitor removal.

        Args:
            name: The monitor name
        """
        try:
            self._monitors.remove(name)
        except ValueError:
            self.log.warning("Monitor %s not found in state - can't be removed", name)


# Keep backwards compatibility alias
StateMonitorTrackingMixin = MonitorTrackingMixin
