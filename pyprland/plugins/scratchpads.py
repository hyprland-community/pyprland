" Scratchpads addon "
import asyncio
import os
import subprocess
from typing import Any, cast
import logging

from ..ipc import get_focused_monitor_props, hyprctl, hyprctlJSON
from .interface import Plugin

DEFAULT_MARGIN = 60


async def get_client_props_by_address(addr: str):
    "Returns client properties given its address"
    assert len(addr) > 2, "Client address is invalid"
    for client in await hyprctlJSON("clients"):
        assert isinstance(client, dict)
        if client.get("address") == addr:
            return client


class Animations:
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


class Scratch:
    "A scratchpad state including configuration & client state"
    log = logging.getLogger("scratch")

    def __init__(self, uid, opts):
        self.uid = uid
        self.pid = 0
        self.conf = opts
        self.visible = False
        self.just_created = True
        self.client_info = {}

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
        self.just_created = True
        self.client_info = {}

    @property
    def address(self) -> str:
        "Returns the client address"
        return str(self.client_info.get("address", ""))[2:]

    async def updateClientInfo(self, client_info=None) -> None:
        "update the internal client info property, if not provided, refresh based on the current address"
        if client_info is None:
            client_info = await get_client_props_by_address("0x" + self.address)
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


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    procs: dict[str, subprocess.Popen] = {}
    scratches: dict[str, Scratch] = {}
    transitioning_scratches: set[str] = set()
    _new_scratches: set[str] = set()
    _respawned_scratches: set[str] = set()
    scratches_by_address: dict[str, Scratch] = {}
    scratches_by_pid: dict[int, Scratch] = {}
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

        new_scratches = set()

        for name in scratches:
            if name not in self.scratches:
                self.scratches[name] = scratches[name]
                new_scratches.add(name)
            else:
                self.scratches[name].conf = scratches[name].conf

        # not known yet
        for name in new_scratches:
            if not self.scratches[name].conf.get("lazy", False):
                await self.start_scratch_command(name, is_new=True)

    async def start_scratch_command(self, name: str, is_new=False) -> None:
        "spawns a given scratchpad's process"
        if is_new:
            self._new_scratches.add(name)
        self._respawned_scratches.add(name)
        scratch = self.scratches[name]
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
        self.scratches[name].reset(pid)
        self.scratches_by_pid[pid] = scratch
        self.log.info(f"scratch {scratch.uid} has pid {pid}")

        if old_pid and old_pid in self.scratches_by_pid:
            del self.scratches_by_pid[old_pid]

    # Events
    async def event_activewindowv2(self, addr) -> None:
        "active windows hook"
        addr = addr.strip()
        scratch = self.scratches_by_address.get(addr)
        if scratch:
            if scratch.just_created:
                self.log.debug("Hiding just created scratch %s", scratch.uid)
                await self.run_hide(scratch.uid, force=True)
                scratch.just_created = False
        else:
            for uid, scratch in self.scratches.items():
                if scratch.client_info and scratch.address != addr:
                    if (
                        scratch.visible
                        and scratch.conf.get("unfocus") == "hide"
                        and scratch.uid not in self.transitioning_scratches
                    ):
                        self.log.debug("hide %s because another client is active", uid)
                        await self.run_hide(uid, autohide=True)

    async def _alternative_lookup(self):
        "if class attribute is defined, use class matching and return True"
        class_lookup_hack = [
            self.scratches[name]
            for name in self._respawned_scratches
            if self.scratches[name].conf.get("class")
        ]
        if not class_lookup_hack:
            return False
        self.log.debug("Lookup hack triggered")
        # hack to update the client info from the provided class
        for client in await hyprctlJSON("clients"):
            assert isinstance(client, dict)
            for pending_scratch in class_lookup_hack:
                if pending_scratch.conf["class"] == client["class"]:
                    self.scratches_by_address[client["address"][2:]] = pending_scratch
                    self.log.debug("client class found: %s", client)
                    await pending_scratch.updateClientInfo(client)
        return True

    async def event_openwindow(self, params) -> None:
        "open windows hook"
        addr, wrkspc, _kls, _title = params.split(",", 3)
        if self._respawned_scratches:
            item = self.scratches_by_address.get(addr)
            if not item and self._respawned_scratches:
                # hack for windows which aren't related to the process (see #8)
                if not await self._alternative_lookup():
                    await self.updateScratchInfo()
                item = self.scratches_by_address.get(addr)
            if item and item.just_created:
                if item.uid in self._new_scratches:
                    await self.run_hide(item.uid, force=True)
                self._new_scratches.discard(item.uid)
                self._respawned_scratches.discard(item.uid)
                item.just_created = False

    async def run_toggle(self, uid: str) -> None:
        """<name> toggles visibility of scratchpad "name" """
        uid = uid.strip()
        item = self.scratches.get(uid)
        if not item:
            self.log.warning("%s is not configured", uid)
            return
        self.log.debug("%s is visible = %s", uid, item.visible)
        if item.visible:
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

        if scratch.uid in self.transitioning_scratches:
            return  # abort sequence
        await asyncio.sleep(0.2)  # await for animation to finish

    async def updateScratchInfo(self, scratch: Scratch | None = None) -> None:
        """Update every scratchpads information if no `scratch` given,
        else update a specific scratchpad info"""
        if scratch is None:
            for client in await hyprctlJSON("clients"):
                assert isinstance(client, dict)
                scratch = self.scratches_by_address.get(client["address"][2:])
                if not scratch:
                    scratch = self.scratches_by_pid.get(client["pid"])
                    if scratch:
                        self.scratches_by_address[client["address"][2:]] = scratch
                if scratch:
                    await scratch.updateClientInfo(client)
        else:
            add_to_address_book = ("address" not in scratch.client_info) or (
                scratch.address not in self.scratches_by_address
            )
            await scratch.updateClientInfo()
            if add_to_address_book:
                self.scratches_by_address[scratch.client_info["address"][2:]] = scratch

    async def run_hide(self, uid: str, force=False, autohide=False) -> None:
        """<name> hides scratchpad "name" """
        uid = uid.strip()
        scratch = self.scratches.get(uid)
        if not scratch:
            self.log.warning("%s is not configured", uid)
            return
        if not scratch.visible and not force:
            self.log.warning("%s is already hidden", uid)
            return
        self.log.info("Hiding %s", uid)
        scratch.visible = False
        addr = "address:0x" + scratch.address
        animation_type: str = scratch.conf.get("animation", "").lower()
        if animation_type:
            await self._anim_hide(animation_type, scratch)

        if uid not in self.transitioning_scratches:
            await hyprctl(f"movetoworkspacesilent special:scratch_{uid},{addr}")

        if (
            animation_type and uid in self.focused_window_tracking
        ):  # focus got lost when animating
            if not autohide and "address" in self.focused_window_tracking[uid]:
                await hyprctl(
                    f"focuswindow address:{self.focused_window_tracking[uid]['address']}"
                )
                del self.focused_window_tracking[uid]

    async def run_show(self, uid, force=False) -> None:
        """<name> shows scratchpad "name" """
        uid = uid.strip()
        item = self.scratches.get(uid)

        self.focused_window_tracking[uid] = cast(
            dict[str, Any], await hyprctlJSON("activewindow")
        )

        if not item:
            self.log.warning("%s is not configured", uid)
            return

        if item.visible and not force:
            self.log.warning("%s is already visible", uid)
            return

        self.log.info("Showing %s", uid)

        if not item.isAlive():
            self.log.info("%s is not running, restarting...", uid)
            if uid in self.procs:
                self.procs[uid].kill()
            if item.pid in self.scratches_by_pid:
                del self.scratches_by_pid[item.pid]
            if item.address in self.scratches_by_address:
                del self.scratches_by_address[item.address]
            self.log.info(f"starting {uid}")
            await self.start_scratch_command(uid)
            self.log.info(f"{uid} started")
            self.log.info("==> Wait for spawning")
            while uid in self._respawned_scratches:
                await asyncio.sleep(0.05)
            self.log.info("<== spawned!")

        item.visible = True
        monitor = await get_focused_monitor_props()
        assert monitor

        await self.updateScratchInfo(item)

        assert item.address, "No address !"

        addr = "address:0x" + item.address

        animation_type = item.conf.get("animation", "").lower()

        wrkspc = monitor["activeWorkspace"]["id"]

        self.transitioning_scratches.add(uid)
        await hyprctl(f"moveworkspacetomonitor special:scratch_{uid} {monitor['name']}")
        await hyprctl(f"movetoworkspacesilent {wrkspc},{addr}")
        if animation_type:
            margin = item.conf.get("margin", DEFAULT_MARGIN)
            fn = getattr(Animations, animation_type)
            await fn(monitor, item.client_info, addr, margin)

        await hyprctl(f"focuswindow {addr}")

        size = item.conf.get("size")
        if size:
            x_size, y_size = self._convert_coords(size, monitor)
            await hyprctl(f"resizewindowpixel exact {x_size} {y_size},{addr}")

        position = item.conf.get("position")
        if position:
            x_pos, y_pos = self._convert_coords(position, monitor)
            x_pos_abs, y_pos_abs = x_pos + monitor["x"], y_pos + monitor["y"]
            await hyprctl(f"movewindowpixel exact {x_pos_abs} {y_pos_abs},{addr}")

        await asyncio.sleep(0.2)  # ensure some time for events to propagate
        self.transitioning_scratches.discard(uid)

    def _convert_coords(self, coords, monitor):
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
            self.log.error(f"Failed to read coordinates: {e}")
            raise e
