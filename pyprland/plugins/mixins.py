"""Reusable mixins for plugins."""

from typing import Any


class MonitorTrackingMixin:
    """Mixin for plugins that need to track monitor add/remove events.

    Plugins using this mixin should define a `monitors` attribute (list[str])
    that will be automatically updated when monitors are added/removed.

    Example usage:
        class Extension(MonitorTrackingMixin, Plugin):
            monitors: list[str] = []

            async def init(self):
                self.monitors = [m["name"] for m in await self.backend.get_monitors()]
    """

    # These attributes are provided by the Plugin class
    log: Any
    monitors: list[str]

    async def event_monitoradded(self, name: str) -> None:
        """Track monitor addition.

        Args:
            name: The monitor name
        """
        self.monitors.append(name)

    async def event_monitorremoved(self, name: str) -> None:
        """Track monitor removal.

        Args:
            name: The monitor name
        """
        try:
            self.monitors.remove(name)
        except ValueError:
            self.log.warning("Monitor %s not found in state - can't be removed", name)


class StateMonitorTrackingMixin:
    """Mixin for core plugins that track monitors in SharedState.

    This is used by the pyprland core plugin (HyprlandStateMixin) which
    stores monitor list in self.state.monitors instead of self.monitors.
    """

    # These attributes are provided by the Plugin/Mixin class
    log: Any
    state: Any

    async def event_monitoradded(self, name: str) -> None:
        """Track monitor addition in shared state.

        Args:
            name: The monitor name
        """
        self.state.monitors.append(name)

    async def event_monitorremoved(self, name: str) -> None:
        """Track monitor removal from shared state.

        Args:
            name: The monitor name
        """
        try:
            self.state.monitors.remove(name)
        except ValueError:
            self.log.warning("Monitor %s not found in state - can't be removed", name)
