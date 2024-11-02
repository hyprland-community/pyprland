"""Scratchpad object definition."""

__all__ = ["Scratch"]

import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, cast

from ...aioops import aiexists, aiopen
from ...common import CastBoolMixin, state
from ...types import ClientInfo, MonitorInfo, VersionInfo
from .helpers import DynMonitorConfig, get_match_fn

if TYPE_CHECKING:
    from collections.abc import Callable

    import pyprland.plugins.scratchpads as _scratchpads_extension_m

    class ClientPropGetter(Protocol):
        """type for the get_client_props function."""

        async def __call__(self, match_fn: Callable | None = None, clients: list[ClientInfo] | None = None, **kw) -> ClientInfo | None:
            pass


@dataclass
class MetaInfo:
    """Meta properties."""

    initialized: bool = False
    should_hide: bool = False
    no_pid: bool = False
    last_shown: float | int = 0
    space_identifier: tuple[str, str] = ("", "")
    monitor_info: MonitorInfo = None  # type: ignore
    extra_positions: dict[str, tuple[int, int]] = field(default_factory=dict)


class Scratch(CastBoolMixin):  # {{{
    """A scratchpad state including configuration & client state."""

    log = logging.getLogger("scratch")
    get_client_props: "ClientPropGetter"
    client_info: ClientInfo
    visible = False
    uid = ""
    monitor = ""
    pid = -1
    excluded_scratches: list[str] = []

    def __init__(self, uid: str, opts: dict[str, Any]) -> None:
        self.uid = uid
        self.set_config(opts)
        self.client_info: ClientInfo = {}  # type: ignore
        self.meta = MetaInfo()
        self.extra_addr: set[str] = set()  # additional client addresses

    @property
    def forced_monitor(self) -> str | None:
        """Returns forced monitor if available, else None."""
        forced_monitor = self.conf.get("force_monitor")
        if forced_monitor in state.monitors:
            return cast(str, forced_monitor)
        return None

    def _make_intial_config(self, config: dict) -> dict:
        """Return configuration for the scratchpad."""
        opts = {}
        scratch_config = config[self.uid]
        if "use" in scratch_config:
            inheritance = scratch_config["use"]
            if isinstance(inheritance, str):
                inheritance = [inheritance]

            for source in inheritance:
                if source in config:
                    opts.update(config[source])
                else:
                    text = f"Scratchpad {self.uid} tried to use {source}, but it doesn't exist"
                    self.log.exception(text)
        opts.update(scratch_config)
        return opts

    def set_config(self, full_config: dict[str, Any]) -> None:
        """Apply constraints to the configuration."""
        opts = self._make_intial_config(full_config)

        # apply the config
        self.conf = DynMonitorConfig(opts, opts.get("monitor", {}))

        # apply constraints
        if self.cast_bool(opts.get("preserve_aspect")):
            opts["lazy"] = True
        if not self.have_command:
            opts["match_by"] = "class"
        if not opts.get("process_tracking", True):
            opts["lazy"] = True
            if "match_by" not in opts:
                opts["match_by"] = "class"
        if state.hyprland_version < VersionInfo(0, 39, 0):
            opts["allow_special_workspace"] = False

    def have_address(self, addr: str) -> bool:
        """Check if the address is the same as the client."""
        return addr == self.full_address or addr in self.extra_addr

    @property
    def have_command(self) -> bool:
        """Check if the command is provided."""
        return bool(self.conf.get("command"))

    async def initialize(self, ex: "_scratchpads_extension_m.Extension") -> None:
        """Initialize the scratchpad."""
        if self.meta.initialized:
            return
        if self.have_command:
            await self.update_client_info()
        else:
            m_client = await self.fetch_matching_client()
            if m_client:
                self.client_info = m_client
            assert self.client_info, "couldn't find a matching client"
        await ex.hyprctl(f"movetoworkspacesilent special:scratch_{self.uid},address:{self.full_address}")
        self.meta.initialized = True

    async def is_alive(self) -> bool:
        """Is the process running ?."""
        if not self.have_command:
            return True
        if self.cast_bool(self.conf.get("process_tracking"), True):
            path = f"/proc/{self.pid}"
            if await aiexists(path):
                async with aiopen(os.path.join(path, "status"), mode="r", encoding="utf-8") as f:
                    for line in await f.readlines():
                        if line.startswith("State"):
                            proc_state = line.split()[1]
                            return proc_state not in "ZX"  # not "Z (zombie)"or "X (dead)"
        else:
            if self.meta.no_pid:
                return bool(await self.fetch_matching_client())
            return False

        return False

    async def fetch_matching_client(self, clients: list[ClientInfo] | None = None) -> ClientInfo | None:
        """Fetch the first matching client properties."""
        match_by, match_val = self.get_match_props()
        return await self.get_client_props(
            match_fn=get_match_fn(match_by, match_val),
            clients=clients,
            **{match_by: match_val},
        )

    def get_match_props(self) -> tuple[str, str | float]:
        """Return the match properties for the scratchpad."""
        match_by = self.conf.get("match_by", "pid")
        return match_by, self.pid if match_by == "pid" else self.conf[match_by]

    def reset(self, pid: int) -> None:
        """Clear the object."""
        self.pid = pid
        self.visible = False
        self.client_info = {}  # type: ignore
        self.meta.initialized = False

    @property
    def address(self) -> str:
        """Return the client address."""
        return self.client_info.get("address", "")[2:]

    @property
    def full_address(self) -> str:
        """Return the client address."""
        return cast(str, self.client_info.get("address", ""))

    async def update_client_info(
        self,
        client_info: ClientInfo | None = None,
        clients: list[ClientInfo] | None = None,
    ) -> None:
        """Update the internal client info property, if not provided, refresh based on the current address."""
        if client_info is None:
            if self.have_command:
                client_info = await self.get_client_props(addr=self.full_address, clients=clients)
            else:
                client_info = await self.fetch_matching_client(clients=clients)

        if client_info is None:
            self.log.error("The client window %s vanished", self.full_address)
            msg = f"Client window {self.full_address} not found"
            raise KeyError(msg)

        self.client_info.update(client_info)

    def event_workspace(self, name: str) -> None:
        """Check if the workspace changed."""
        if self.conf.get("pinned", True):
            self.meta.space_identifier = name, self.meta.space_identifier[1]

    def __str__(self) -> str:
        return f"{self.uid} {self.address} : {self.client_info} / {self.conf}"


# }}}
# }}}
