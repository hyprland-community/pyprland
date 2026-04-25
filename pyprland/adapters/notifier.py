"""Notification backend abstraction.

Provides a Notifier interface and concrete implementations for different
notification mechanisms. The notifier is selected once at startup and
injected into BackendProxy, so no runtime conditionals are needed.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from logging import Logger
from typing import TYPE_CHECKING, Any, TypeAlias

from ..constants import DEFAULT_NOTIFICATION_DURATION_MS
from ..utils import notify_send

if TYPE_CHECKING:
    from .backend import EnvironmentBackend

# Type alias for the execute function passed to HyprlandNotifier
ExecuteFn: TypeAlias = Callable[..., Coroutine[Any, Any, bool]]

# Registry mapping notification_type config values to factory functions.
# "auto" and "native" are resolved via the backend's get_default_notifier().
# Additional notifier types can be registered here.
_NOTIFIER_REGISTRY: dict[str, type["Notifier"]] = {}


def _register(name: str) -> Callable[[type["Notifier"]], type["Notifier"]]:
    """Class decorator to register a Notifier implementation under a config name."""

    def decorator(cls: type["Notifier"]) -> type["Notifier"]:
        _NOTIFIER_REGISTRY[name] = cls
        return cls

    return decorator


def resolve_notifier(notification_type: str, backend: "EnvironmentBackend") -> "Notifier":
    """Resolve a Notifier instance from a notification_type config value.

    Args:
        notification_type: The user's config value ("auto", "native", "notify-send", etc.)
        backend: The active compositor backend (provides the default/native notifier)

    Returns:
        The resolved Notifier instance
    """
    if notification_type in ("auto", "native"):
        return backend.get_default_notifier()
    notifier_cls = _NOTIFIER_REGISTRY.get(notification_type)
    if notifier_cls is None:
        msg = f"Unknown notification_type: {notification_type!r}. Available: {', '.join(['auto', 'native', *_NOTIFIER_REGISTRY])}"
        raise ValueError(msg)
    return notifier_cls()


class Notifier(ABC):
    """Abstract base class for notification backends."""

    @abstractmethod
    async def notify(self, message: str, duration: int = DEFAULT_NOTIFICATION_DURATION_MS, color: str = "ff0000", *, log: Logger) -> None:
        """Send a notification.

        Args:
            message: The notification message
            duration: Duration in milliseconds
            color: Hex color code
            log: Logger to use for this operation
        """

    async def notify_info(self, message: str, duration: int = DEFAULT_NOTIFICATION_DURATION_MS, *, log: Logger) -> None:
        """Send an info notification.

        Args:
            message: The notification message
            duration: Duration in milliseconds
            log: Logger to use for this operation
        """
        await self.notify(message, duration, "0000ff", log=log)

    async def notify_error(self, message: str, duration: int = DEFAULT_NOTIFICATION_DURATION_MS, *, log: Logger) -> None:
        """Send an error notification.

        Args:
            message: The notification message
            duration: Duration in milliseconds
            log: Logger to use for this operation
        """
        await self.notify(message, duration, "ff0000", log=log)


@_register("notify-send")
class NotifySendNotifier(Notifier):
    """Notification backend using the notify-send command."""

    async def notify(
        self,
        message: str,
        duration: int = DEFAULT_NOTIFICATION_DURATION_MS,
        color: str = "ff0000",
        *,
        log: Logger,
    ) -> None:
        """Send a notification via notify-send."""
        del log
        await notify_send(message, duration, color)


class HyprlandNotifier(Notifier):
    """Notification backend using Hyprland's native IPC.

    Uses hyprctl notify with icon codes and RGB colors.
    """

    def __init__(self, execute_fn: ExecuteFn) -> None:
        """Initialize with a reference to the backend's execute method.

        Args:
            execute_fn: Async callable matching EnvironmentBackend.execute signature
        """
        self._execute = execute_fn

    async def notify(self, message: str, duration: int = DEFAULT_NOTIFICATION_DURATION_MS, color: str = "ff1010", *, log: Logger) -> None:
        """Send a notification via Hyprland IPC."""
        await self._execute(f"-1 {duration} rgb({color})  {message}", log=log, base_command="notify")

    async def notify_info(self, message: str, duration: int = DEFAULT_NOTIFICATION_DURATION_MS, *, log: Logger) -> None:
        """Send an info notification via Hyprland IPC (icon=1)."""
        await self._execute(f"1 {duration} rgb(1010ff)  {message}", log=log, base_command="notify")

    async def notify_error(self, message: str, duration: int = DEFAULT_NOTIFICATION_DURATION_MS, *, log: Logger) -> None:
        """Send an error notification via Hyprland IPC (icon=0)."""
        await self._execute(f"0 {duration} rgb(ff1010)  {message}", log=log, base_command="notify")
