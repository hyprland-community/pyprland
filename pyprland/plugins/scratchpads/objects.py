" Scratchpad object definition "

__all__ = ["Scratch"]

import os
import logging
from typing import Callable, cast
from collections import defaultdict

from aiofiles import os as aios
from aiofiles import open as aiopen

from ...ipc import notify_error
from ...common import CastBoolMixin, VersionInfo, state, ClientInfo
from .helpers import OverridableConfig, get_match_fn


class Scratch(CastBoolMixin):  # {{{
    "A scratchpad state including configuration & client state"
    log = logging.getLogger("scratch")
    get_client_props: Callable
    client_info: ClientInfo
    visible = False
    uid = ""
    monitor = ""
    pid = -1

    def __init__(self, uid, opts):
        self.uid = uid
        self.set_config(OverridableConfig(opts, opts.get("monitor", {})))
        self.client_info: ClientInfo = {}  # type: ignore
        self.meta = defaultdict(lambda: False)
        self.extra_addr: set[str] = set()  # additional client addresses

    def set_config(self, opts):
        "Apply constraints to the configuration"
        if "class_match" in opts:  # NOTE: legacy, to be removed
            opts["match_by"] = "class"
        if self.cast_bool(opts.get("preserve_aspect")):
            opts["lazy"] = True
        if not opts.get("process_tracking", True):
            opts["lazy"] = True
            if "match_by" not in opts:
                opts["match_by"] = "class"
        if state.hyprland_version < VersionInfo(0, 39, 0):
            opts["allow_special_workspace"] = False

        self.conf = opts

    async def initialize(self, ex):
        "Initialize the scratchpad"
        if self.meta["initialized"]:
            return
        self.meta["initialized"] = True
        await self.updateClientInfo()
        await ex.hyprctl(
            f"movetoworkspacesilent special:scratch_{self.uid},address:{self.full_address}"
        )
        if "class_match" in self.conf:  # NOTE: legacy, to be removed
            await notify_error(
                f'scratchpad {self.uid} should use match_by="class" instead of the deprecated class_match',
                logger=self.log,
            )

    async def isAlive(self) -> bool:
        "is the process running ?"
        if self.cast_bool(self.conf.get("process_tracking"), True):
            path = f"/proc/{self.pid}"
            if await aios.path.exists(path):
                async with aiopen(
                    os.path.join(path, "status"), mode="r", encoding="utf-8"
                ) as f:
                    for line in await f.readlines():
                        if line.startswith("State"):
                            proc_state = line.split()[1]
                            return (
                                proc_state not in "ZX"
                            )  # not "Z (zombie)"or "X (dead)"
        else:
            if "nopid" in self.meta:
                match_by = self.conf["match_by"]
                match_value = self.conf[match_by]
                match_fn = get_match_fn(match_by, match_value)
                return bool(
                    await self.get_client_props(
                        match_fn=match_fn, **{match_by: match_value}
                    )
                )
            return False

        return False

    def reset(self, pid: int) -> None:
        "clear the object"
        self.pid = pid
        self.visible = False
        self.client_info = {}  # type: ignore
        self.meta["initialized"] = False

    @property
    def address(self) -> str:
        "Returns the client address"
        return self.client_info.get("address", "")[2:]

    @property
    def full_address(self) -> str:
        "Returns the client address"
        return cast(str, self.client_info.get("address", ""))

    async def updateClientInfo(self, client_info: ClientInfo | None = None) -> None:
        "update the internal client info property, if not provided, refresh based on the current address"
        if client_info is None:
            client_info = await self.get_client_props(addr=self.full_address)
        if not isinstance(client_info, dict):
            if client_info is None:
                self.log.error("The client window %s vanished", self.full_address)
                raise AssertionError(f"Client window {self.full_address} not found")
            self.log.error(
                "client_info of %s must be a dict: %s", self.address, client_info
            )
            raise AssertionError(f"Not a dict: {client_info}")

        self.client_info.update(client_info)

    def __str__(self):
        return f"{self.uid} {self.address} : {self.client_info} / {self.conf}"


# }}}
