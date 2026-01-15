"""Backend adapter interface."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from ..common import SharedState, get_logger
from ..models import ClientInfo, MonitorInfo


class EnvironmentBackend(ABC):
    """Abstract base class for environment backends (Hyprland, Niri, etc)."""

    def __init__(self, state: SharedState) -> None:
        self.state = state
        self.log = get_logger("backend")

    @abstractmethod
    async def get_clients(
        self,
        mapped: bool = True,
        workspace: str | None = None,
        workspace_bl: str | None = None,
    ) -> list[ClientInfo]:
        """Return the list of clients, optionally filtered."""

    @abstractmethod
    async def get_monitors(self) -> list[MonitorInfo]:
        """Return the list of monitors."""

    async def get_monitor_props(self, name: str | None = None) -> MonitorInfo:
        """Return focused monitor data if `name` is not defined, else use monitor's name."""
        monitors = await self.get_monitors()
        if name:
            for mon in monitors:
                if mon["name"] == name:
                    return mon
        else:
            for mon in monitors:
                if mon.get("focused"):
                    return mon
        msg = "no focused monitor"
        raise RuntimeError(msg)

    @abstractmethod
    async def execute(self, command: str | list[str], **kwargs: Any) -> bool:  # noqa: ANN401
        """Execute a command (or list of commands)."""

    @abstractmethod
    async def execute_json(self, command: str, **kwargs: Any) -> Any:  # noqa: ANN401
        """Execute a command and return the JSON result."""

    @abstractmethod
    async def execute_batch(self, commands: list[str]) -> None:
        """Execute a batch of commands."""

    @abstractmethod
    async def notify(self, message: str, duration: int = 5000, color: str = "ff0000") -> None:
        """Send a notification."""

    @abstractmethod
    async def notify_info(self, message: str, duration: int = 5000) -> None:
        """Send an info notification."""

    @abstractmethod
    async def notify_error(self, message: str, duration: int = 5000) -> None:
        """Send an error notification."""

    async def get_client_props(
        self,
        match_fn: Callable[[Any, Any], bool] | None = None,
        clients: list[ClientInfo] | None = None,
        **kw: Any,  # noqa: ANN401
    ) -> ClientInfo | None:
        """Return the properties of a client that matches the given `match_fn` (or default to equality) given the keyword arguments.

        This serves as a backend-agnostic implementation, assuming get_clients() returns the list of clients.
        """
        from ..common import MINIMUM_ADDR_LEN  # noqa: PLC0415

        if match_fn is None:

            def default_match_fn(value1: Any, value2: Any) -> bool:  # noqa: ANN401
                return bool(value1 == value2)

            match_fn = default_match_fn

        assert kw

        addr = kw.get("addr")
        klass = kw.get("cls")

        if addr:
            assert len(addr) > MINIMUM_ADDR_LEN, "Client address is invalid"
            prop_name = "address"
            prop_value = addr
        elif klass:
            prop_name = "class"
            prop_value = klass
        else:
            prop_name, prop_value = next(iter(kw.items()))

        clients_list = clients or await self.get_clients(mapped=False)

        for client in clients_list:
            assert isinstance(client, dict)
            val = client.get(prop_name)
            if match_fn(val, prop_value):
                return client
        return None
