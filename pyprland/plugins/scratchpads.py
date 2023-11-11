" Scratchpads addon "
import os
import logging
import asyncio
import subprocess
from typing import Any, cast
from collections import defaultdict

from ..ipc import get_focused_monitor_props, hyprctl, hyprctlJSON
from .interface import Plugin

DEFAULT_MARGIN = 60

# Helper functions {{{


def convert_coords(logger, coords, monitor):
    """
    Converts a string like "X Y" to coordinates relative to monitor
    Supported formats for X, Y:
    - Percentage: "V%". V in [0; 100]

    Example:
    "10% 20%", monitor 800x600 => 80, 120
    """

    assert coords, "coords must be non null"

    def convert(s, dim):
        if s[-1] == "%":
            p = int(s[:-1])
            if p < 0 or p > 100:
                raise Exception(f"Percentage must be in range [0; 100], got {p}")
            scale = float(monitor["scale"])
            return int(monitor[dim] / scale * p / 100)
        else:
            raise Exception(f"Unsupported format for dimension {dim} size, got {s}")

    try:
        x_str, y_str = coords.split()

        return convert(x_str, "width"), convert(y_str, "height")
    except Exception as e:
        logger.error(f"Failed to read coordinates: {e}")
        raise e


async def get_client_props(addr: str | None = None, pid: int | None = None):
    "Returns client properties given its address"
    assert addr or pid
    if addr:
        assert len(addr) > 2, "Client address is invalid"
    if pid:
        assert pid, "Client pid is invalid"
    prop_name = "address" if addr else "pid"
    prop_value = addr if addr else pid
    for client in await hyprctlJSON("clients"):
        assert isinstance(client, dict)
        if client.get(prop_name) == prop_value:
            return client


# }}}


class Animations:  # {{{
    "Animation store"

    @staticmethod
    async def fromtop(monitor, client, client_uid, margin):
        "Slide from/to top"
        scale = float(monitor["scale"])
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width = int(monitor["width"] / scale)

        client_width = client["size"][0]
        margin_x = int((mon_width - client_width) / 2) + mon_x

        await hyprctl(f"movewindowpixel exact {margin_x} {mon_y + margin},{client_uid}")

    @staticmethod
    async def frombottom(monitor, client, client_uid, margin):
        "Slide from/to bottom"
        scale = float(monitor["scale"])
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width = int(monitor["width"] / scale)
        mon_height = int(monitor["height"] / scale)

        client_width = client["size"][0]
        client_height = client["size"][1]
        margin_x = int((mon_width - client_width) / 2) + mon_x
        await hyprctl(
            f"movewindowpixel exact {margin_x} {mon_y + mon_height - client_height - margin},{client_uid}"
        )

    @staticmethod
    async def fromleft(monitor, client, client_uid, margin):
        "Slide from/to left"
        scale = float(monitor["scale"])
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_height = int(monitor["height"] / scale)

        client_height = client["size"][1]
        margin_y = int((mon_height - client_height) / 2) + mon_y

        await hyprctl(f"movewindowpixel exact {margin + mon_x} {margin_y},{client_uid}")

    @staticmethod
    async def fromright(monitor, client, client_uid, margin):
        "Slide from/to right"
        scale = float(monitor["scale"])
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width = int(monitor["width"] / scale)
        mon_height = int(monitor["height"] / scale)

        client_width = client["size"][0]
        client_height = client["size"][1]
        margin_y = int((mon_height - client_height) / 2) + mon_y
        await hyprctl(
            f"movewindowpixel exact {mon_width - client_width - margin + mon_x } {margin_y},{client_uid}"
        )


# }}}


class Scratch:  # {{{
    "A scratchpad state including configuration & client state"
    log = logging.getLogger("scratch")

    def __init__(self, uid, opts):
        self.uid = uid
        self.pid = 0
        self.conf = opts
        self.visible = False
        self.client_info = {}
        self.should_hide = False
        self.initialized = False

    async def initialize(self):
        if self.initialized:
            return
        self.initialized = True
        await self.updateClientInfo()
        await hyprctl(
            f"movetoworkspacesilent special:scratch_{self.uid},address:0x{self.address}"
        )

        size = self.conf.get("size")
        position = self.conf.get("position")
        monitor = await get_focused_monitor_props()
        if position:
            x_pos, y_pos = convert_coords(self.log, position, monitor)
            x_pos_abs, y_pos_abs = x_pos + monitor["x"], y_pos + monitor["y"]
            await hyprctl(
                f"movewindowpixel exact {x_pos_abs} {y_pos_abs},address:0x{self.address}"
            )
        if size:
            x_size, y_size = convert_coords(self.log, size, monitor)
            await hyprctl(
                f"resizewindowpixel exact {x_size} {y_size},address:0x{self.address}"
            )

    def isAlive(self) -> bool:
        "is the process running ?"
        path = f"/proc/{self.pid}"
        if os.path.exists(path):
            with open(os.path.join(path, "status"), "r", encoding="utf-8") as f:
                for line in f.readlines():
                    if line.startswith("State"):
                        state = line.split()[1]
                        return state not in "ZX"  # not "Z (zombie)"or "X (dead)"
        return False

    def reset(self, pid: int) -> None:
        "clear the object"
        self.pid = pid
        self.visible = False
        self.client_info = {}
        self.initialized = False

    @property
    def address(self) -> str:
        "Returns the client address"
        return str(self.client_info.get("address", ""))[2:]

    async def updateClientInfo(self, client_info=None) -> None:
        "update the internal client info property, if not provided, refresh based on the current address"
        if client_info is None:
            client_info = await get_client_props(addr="0x" + self.address)
        try:
            assert isinstance(client_info, dict)
        except AssertionError as e:
            self.log.error(
                f"client_info of {self.address} must be a dict: {client_info}"
            )
            raise AssertionError(e) from e

        self.client_info.update(client_info)

    def __str__(self):
        return f"{self.uid} {self.address} : {self.client_info} / {self.conf}"


# }}}


class ScratchDB:
    """Single storage for every Scratch allowing a boring lookup & update API"""

    _by_addr: dict[str, Scratch] = {}
    _by_pid: dict[int, Scratch] = {}
    _by_name: dict[str, Scratch] = {}
    _states: defaultdict[str, set[Scratch]] = defaultdict(lambda: set())

    def getByState(self, state: str):
        return self._states[state]

    def hasState(self, scratch: Scratch, state: str):
        return scratch in self._states[state]

    def setState(self, scratch: Scratch, state: str):
        self._states[state].add(scratch)

    def clearState(self, scratch: Scratch, state: str):
        self._states[state].remove(scratch)

    def __iter__(self):
        "return all Scratch name"
        return self._by_name.keys()

    def values(self):
        "returns every Scratch"
        return self._by_name.values()

    def items(self):
        "return an iterable list of (name, Scratch)"
        return self._by_name.items()

    def reset(self, scratch: Scratch):
        "clears registered address & pid"
        if scratch.address in self._by_addr:
            del self._by_addr[scratch.address]
        if scratch.pid in self._by_pid:
            del self._by_pid[scratch.pid]

    def clear(self, name=None, pid=None, addr=None):
        "clears the index by name, pid or address"
        assert any((name, pid, addr))
        if name is not None and name in self._by_name:
            del self._by_name[name]
        if pid is not None and pid in self._by_pid:
            del self._by_pid[pid]
        if addr is not None and addr in self._by_addr:
            del self._by_addr[addr]

    def register(self, scratch: Scratch, name=None, pid=None, addr=None):
        "set the Scratch index by name, pid or address"
        assert 1 == len(list(filter(bool, (name, pid, addr))))
        if name is not None:
            d = self._by_name
            v = name
        elif pid is not None:
            d = self._by_pid
            v = pid
        elif addr is not None:
            d = self._by_addr
            v = addr
        d[v] = scratch

    def get(self, name=None, pid=None, addr=None) -> Scratch:
        "return the Scratch matching given name, pid or address"
        assert 1 == len(list(filter((lambda x: bool(x)), (name, pid, addr)))), (
            name,
            pid,
            addr,
        )
        if name is not None:
            d = self._by_name
            v = name
        elif pid is not None:
            d = self._by_pid
            v = pid
        elif addr is not None:
            d = self._by_addr
            v = addr
        return d.get(v)


class Extension(Plugin):  # pylint: disable=missing-class-docstring {{{
    procs: dict[str, subprocess.Popen] = {}
    scratches = ScratchDB()

    focused_window_tracking: dict[str, dict] = {}

    async def exit(self) -> None:
        "exit hook"

        async def die_in_piece(scratch: Scratch):
            proc = self.procs[scratch.uid]
            proc.terminate()
            for _ in range(10):
                if not scratch.isAlive():
                    break
                await asyncio.sleep(0.1)
            if scratch.isAlive():
                proc.kill()
            proc.wait()

        await asyncio.gather(
            *(die_in_piece(scratch) for scratch in self.scratches.values())
        )

    async def load_config(self, config: dict[str, Any]) -> None:
        "config loader"
        my_config: dict[str, dict[str, Any]] = config["scratchpads"]
        scratches = {k: Scratch(k, v) for k, v in my_config.items()}

        scratches_to_spawn = set()
        for name in scratches:
            if not self.scratches.get(name):
                self.scratches.register(scratches[name], name)
                is_lazy = scratches[name].conf.get("lazy", False)
                if not is_lazy:
                    scratches_to_spawn.add(name)
            else:
                self.scratches.get(name).conf = scratches[name].conf

        self.log.info(scratches_to_spawn)
        for name in scratches_to_spawn:
            if await self.ensure_alive(name):
                self.scratches.get(name).should_hide = True
            else:
                self.log.error(f"Failure starting {name}")

    async def ensure_alive(self, uid, item=None):
        if item is None:
            item = self.scratches.get(name=uid)

        if not item.isAlive():
            self.log.info("%s is not running, restarting...", uid)
            if uid in self.procs:
                self.procs[uid].kill()
            self.scratches.reset(item)
            self.log.info(f"starting {uid}")
            await self.start_scratch_command(uid)
            self.log.info(f"==> Wait for {uid} spawning")
            for loop_count in range(1, 8):
                await asyncio.sleep(loop_count**2 / 10.0)
                info = await get_client_props(pid=item.pid)
                if info:
                    self.log.info(f"=> {uid} info received on time")
                    await item.updateClientInfo(info)
                    self.scratches.clearState(item, "respawned")
                    self.log.info(f"=> spawned {uid} as proc {item.pid}")
                    return True
            self.log.error(f"=> Failed spawning {uid} as proc {item.pid}")
            return False
        return True

    async def start_scratch_command(self, name: str) -> None:
        "spawns a given scratchpad's process"
        scratch = self.scratches.get(name)
        self.scratches.setState(scratch, "respawned")
        old_pid = self.procs[name].pid if name in self.procs else 0
        proc = subprocess.Popen(
            scratch.conf["command"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True,
        )
        self.procs[name] = proc
        pid = proc.pid
        scratch.reset(pid)
        self.scratches.register(scratch, pid=pid)
        self.log.info(f"scratch {scratch.uid} has pid {pid}")
        if old_pid:
            self.scratches.clear(pid=old_pid)

    async def updateScratchInfo(self, orig_scratch: Scratch | None = None) -> None:
        """Update every scratchpads information if no `scratch` given,
        else update a specific scratchpad info"""
        pid = orig_scratch.pid if orig_scratch else None
        for client in await hyprctlJSON("clients"):
            assert isinstance(client, dict)
            if pid and pid != client["pid"]:
                continue
            # if no address registered, register it
            # + update client info in any case
            scratch = self.scratches.get(addr=client["address"][2:])
            if not scratch and client["pid"]:
                scratch = self.scratches.get(pid=client["pid"])
            if scratch:
                self.scratches.register(scratch, addr=client["address"][2:])
                await scratch.updateClientInfo(client)
                break
        else:
            self.log.info("Didn't update scratch info %s" % self)

    # Events {{{
    async def event_activewindowv2(self, addr) -> None:
        "active windows hook"
        addr = addr.strip()
        scratch = self.scratches.get(addr=addr)
        if not scratch:
            for uid, scratch in self.scratches.items():
                if scratch.client_info and scratch.address != addr:
                    if (
                        scratch.visible
                        and scratch.conf.get("unfocus") == "hide"
                        and not self.scratches.hasState(scratch, "transition")
                    ):
                        self.log.debug("hide %s because another client is active", uid)
                        await self.run_hide(uid, autohide=True)

    async def _alternative_lookup(self):
        "if class attribute is defined, use class matching and return True"
        class_lookup_hack = [
            s for s in self.scratches.getByState("respawned") if s.conf.get("class")
        ]
        if not class_lookup_hack:
            return False
        self.log.debug("Lookup hack triggered")
        # hack to update the client info from the provided class
        for client in await hyprctlJSON("clients"):
            assert isinstance(client, dict)
            for pending_scratch in class_lookup_hack:
                if pending_scratch.conf["class"] == client["class"]:
                    self.scratches.register(pending_scratch, addr=client["address"][2:])
                    self.log.debug("client class found: %s", client)
                    await pending_scratch.updateClientInfo(client)
        return True

    async def event_openwindow(self, params) -> None:
        "open windows hook"
        addr, wrkspc, _kls, _title = params.split(",", 3)
        item = self.scratches.get(addr=addr)
        rs = list(self.scratches.getByState("respawned"))
        if rs and not item:
            # hack for windows which aren't related to the process (see #8)
            if not await self._alternative_lookup():
                self.log.info("Updating Scratch info")
                await self.updateScratchInfo()
            item = self.scratches.get(addr=addr)
            if item and item.should_hide:
                await self.run_hide(item.uid, force=True)
        if item:
            await item.initialize()

    # }}}
    # Commands {{{
    async def run_toggle(self, uid: str) -> None:
        """<name> toggles visibility of scratchpad "name" """
        uid = uid.strip()
        item = self.scratches.get(uid)
        if not item:
            self.log.warning("%s is not configured", uid)
            return
        self.log.debug("%s is visible = %s", uid, item.visible)
        if item.visible and item.isAlive():
            await self.run_hide(uid)
        else:
            await self.run_show(uid)

    async def _anim_hide(self, animation_type, scratch):
        "animate hiding a scratchpad"
        addr = "address:0x" + scratch.address
        offset = scratch.conf.get("offset")
        if offset is None:
            if "size" not in scratch.client_info:
                await self.updateScratchInfo(scratch)

            offset = int(1.3 * scratch.client_info["size"][1])

        if animation_type == "fromtop":
            await hyprctl(f"movewindowpixel 0 -{offset},{addr}")
        elif animation_type == "frombottom":
            await hyprctl(f"movewindowpixel 0 {offset},{addr}")
        elif animation_type == "fromleft":
            await hyprctl(f"movewindowpixel -{offset} 0,{addr}")
        elif animation_type == "fromright":
            await hyprctl(f"movewindowpixel {offset} 0,{addr}")

        if self.scratches.hasState(scratch, "transition"):
            return  # abort sequence
        await asyncio.sleep(0.2)  # await for animation to finish

    async def run_show(self, uid) -> None:
        """<name> shows scratchpad "name" """
        uid = uid.strip()
        item = self.scratches.get(uid)

        self.focused_window_tracking[uid] = cast(
            dict[str, Any], await hyprctlJSON("activewindow")
        )

        if not item:
            self.log.warning("%s is not configured", uid)
            return

        self.log.info("Showing %s", uid)
        if not await self.ensure_alive(uid, item):
            self.log.error(f"Failed to show {uid}, aborting.")
            return

        excluded = item.conf.get("excludes", [])
        if excluded == "*":
            excluded = [
                scratch.uid for scratch in self.scratches.values() if scratch.uid != uid
            ]
        for tbh_scratch in excluded:
            self.log.info("hidding ")
            await self.run_hide(tbh_scratch, autohide=True)
        await item.updateClientInfo()
        await item.initialize()

        item.visible = True
        monitor = await get_focused_monitor_props()
        assert monitor

        assert item.address, "No address !"

        addr = "address:0x" + item.address

        animation_type = item.conf.get("animation", "").lower()

        wrkspc = monitor["activeWorkspace"]["id"]

        self.scratches.setState(item, "transition")
        await hyprctl(f"moveworkspacetomonitor special:scratch_{uid} {monitor['name']}")
        await hyprctl(f"movetoworkspacesilent {wrkspc},{addr}")
        if animation_type:
            margin = item.conf.get("margin", DEFAULT_MARGIN)
            fn = getattr(Animations, animation_type)
            await fn(monitor, item.client_info, addr, margin)

        await hyprctl(f"focuswindow {addr}")

        await asyncio.sleep(0.2)  # ensure some time for events to propagate
        self.scratches.clearState(item, "transition")

    async def run_hide(self, uid: str, force=False, autohide=False) -> None:
        """<name> hides scratchpad "name"
        if `autohide` is True, skips focus tracking
        `force` ignores the visibility check"""
        uid = uid.strip()
        scratch = self.scratches.get(uid)
        if not scratch:
            self.log.warning("%s is not configured", uid)
            return
        if not scratch.visible and not force:
            self.log.warning("%s is already hidden", uid)
            return
        scratch.visible = False
        self.log.info("Hiding %s", uid)
        addr = "address:0x" + scratch.address
        animation_type: str = scratch.conf.get("animation", "").lower()
        if animation_type:
            await self._anim_hide(animation_type, scratch)

        if not self.scratches.hasState(scratch, "transition"):
            await hyprctl(f"movetoworkspacesilent special:scratch_{uid},{addr}")

        if (
            animation_type and uid in self.focused_window_tracking
        ):  # focus got lost when animating
            if not autohide and "address" in self.focused_window_tracking[uid]:
                await hyprctl(
                    f"focuswindow address:{self.focused_window_tracking[uid]['address']}"
                )
                del self.focused_window_tracking[uid]

    # }}}


# }}}
