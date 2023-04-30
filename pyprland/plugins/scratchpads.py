import subprocess
from typing import Any
import asyncio
from ..ipc import (
    hyprctl,
    hyprctlJSON,
    get_focused_monitor_props,
)
import os

from .interface import Plugin

DEFAULT_MARGIN = 60


async def get_client_props_by_address(addr: str):
    for client in await hyprctlJSON("clients"):
        assert isinstance(client, dict)
        if client.get("address") == addr:
            return client


class Animations:
    @classmethod
    async def fromtop(cls, monitor, client, client_uid, margin):
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width = monitor["width"]

        client_width = client["size"][0]
        margin_x = int((mon_width - client_width) / 2) + mon_x
        await hyprctl(f"movewindowpixel exact {margin_x} {mon_y + margin},{client_uid}")

    @classmethod
    async def frombottom(cls, monitor, client, client_uid, margin):
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width = monitor["width"]
        mon_height = monitor["height"]

        client_width = client["size"][0]
        client_height = client["size"][1]
        margin_x = int((mon_width - client_width) / 2) + mon_x
        await hyprctl(
            f"movewindowpixel exact {margin_x} {mon_y + mon_height - client_height - margin},{client_uid}"
        )

    @classmethod
    async def fromleft(cls, monitor, client, client_uid, margin):
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_height = monitor["height"]

        client_height = client["size"][1]
        margin_y = int((mon_height - client_height) / 2) + mon_y

        await hyprctl(f"movewindowpixel exact {margin + mon_x} {margin_y},{client_uid}")

    @classmethod
    async def fromright(cls, monitor, client, client_uid, margin):
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width = monitor["width"]
        mon_height = monitor["height"]

        client_width = client["size"][0]
        client_height = client["size"][1]
        margin_y = int((mon_height - client_height) / 2) + mon_y
        await hyprctl(
            f"movewindowpixel exact {mon_width - client_width - margin + mon_x } {margin_y},{client_uid}"
        )


class Scratch:
    def __init__(self, uid, opts):
        self.uid = uid
        self.pid = 0
        self.conf = opts
        self.visible = False
        self.just_created = True
        self.clientInfo = {}

    def isAlive(self) -> bool:
        path = f"/proc/{self.pid}"
        if os.path.exists(path):
            for line in open(os.path.join(path, "status"), "r").readlines():
                if line.startswith("State"):
                    state = line.split()[1]
                    return state in "RSDTt"  # not "Z (zombie)"or "X (dead)"
        return False

    def reset(self, pid: int) -> None:
        self.pid = pid
        self.visible = False
        self.just_created = True
        self.clientInfo = {}

    @property
    def address(self) -> str:
        return str(self.clientInfo.get("address", ""))[2:]

    async def updateClientInfo(self, clientInfo=None) -> None:
        if clientInfo is None:
            clientInfo = await get_client_props_by_address("0x" + self.address)
        assert isinstance(clientInfo, dict)
        self.clientInfo.update(clientInfo)


class Extension(Plugin):
    async def init(self) -> None:
        self.procs: dict[str, subprocess.Popen] = {}
        self.scratches: dict[str, Scratch] = {}
        self.transitioning_scratches: set[str] = set()
        self._respawned_scratches: set[str] = set()
        self.scratches_by_address: dict[str, Scratch] = {}
        self.scratches_by_pid: dict[int, Scratch] = {}
        self.focused_window_tracking = dict()

    async def exit(self) -> None:
        async def die_in_piece(scratch: Scratch):
            proc = self.procs[scratch.uid]
            proc.terminate()
            for n in range(10):
                if not scratch.isAlive():
                    break
                await asyncio.sleep(0.1)
            if scratch.isAlive():
                proc.kill()
            proc.wait()

        await asyncio.gather(
            *(die_in_piece(scratch) for scratch in self.scratches.values())
        )

    async def load_config(self, config) -> None:
        config: dict[str, dict[str, Any]] = config["scratchpads"]
        scratches = {k: Scratch(k, v) for k, v in config.items()}

        new_scratches = set()

        for name in scratches:
            if name not in self.scratches:
                self.scratches[name] = scratches[name]
                new_scratches.add(name)
            else:
                self.scratches[name].conf = scratches[name].conf

        # not known yet
        for name in new_scratches:
            self.start_scratch_command(name)

    def start_scratch_command(self, name: str) -> None:
        self._respawned_scratches.add(name)
        scratch = self.scratches[name]
        old_pid = self.procs[name].pid if name in self.procs else 0
        self.procs[name] = subprocess.Popen(
            scratch.conf["command"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True,
        )
        pid = self.procs[name].pid
        self.scratches[name].reset(pid)
        self.scratches_by_pid[self.procs[name].pid] = scratch
        if old_pid and old_pid in self.scratches_by_pid:
            del self.scratches_by_pid[old_pid]

    # Events
    async def event_activewindowv2(self, addr) -> None:
        addr = addr.strip()
        scratch = self.scratches_by_address.get(addr)
        if scratch:
            if scratch.just_created:
                await self.run_hide(scratch.uid, force=True)
                scratch.just_created = False
        else:
            for uid, scratch in self.scratches.items():
                if scratch.clientInfo and scratch.address != addr:
                    if (
                        scratch.visible
                        and scratch.conf.get("unfocus") == "hide"
                        and scratch.uid not in self.transitioning_scratches
                    ):
                        await self.run_hide(uid, autohide=True)

    async def event_openwindow(self, params) -> None:
        addr, wrkspc, kls, title = params.split(",", 3)
        if wrkspc.startswith("special"):
            item = self.scratches_by_address.get(addr)
            if not item and self._respawned_scratches:
                await self.updateScratchInfo()
                item = self.scratches_by_address.get(addr)
            if item and item.just_created:
                self._respawned_scratches.discard(item.uid)
                await self.run_hide(item.uid, force=True)
                item.just_created = False

    async def run_toggle(self, uid: str) -> None:
        """<name> toggles visibility of scratchpad "name" """
        uid = uid.strip()
        item = self.scratches.get(uid)
        if not item:
            print(f"{uid} is not configured")
            return
        if item.visible:
            await self.run_hide(uid)
        else:
            await self.run_show(uid)

    async def updateScratchInfo(self, scratch: Scratch | None = None) -> None:
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
            add_to_address_book = ("address" not in scratch.clientInfo) or (
                scratch.address not in self.scratches_by_address
            )
            await scratch.updateClientInfo()
            if add_to_address_book:
                self.scratches_by_address[scratch.clientInfo["address"][2:]] = scratch

    async def run_hide(self, uid: str, force=False, autohide=False) -> None:
        """<name> hides scratchpad "name" """
        uid = uid.strip()
        item = self.scratches.get(uid)
        if not item:
            print(f"{uid} is not configured")
            return
        if not item.visible and not force:
            print(f"{uid} is already hidden")
            return
        item.visible = False
        addr = "address:0x" + item.address
        animation_type: str = item.conf.get("animation", "").lower()
        if animation_type:
            offset = item.conf.get("offset")
            if offset is None:
                if "size" not in item.clientInfo:
                    await self.updateScratchInfo(item)

                offset = int(1.3 * item.clientInfo["size"][1])

            if animation_type == "fromtop":
                await hyprctl(f"movewindowpixel 0 -{offset},{addr}")
            elif animation_type == "frombottom":
                await hyprctl(f"movewindowpixel 0 {offset},{addr}")
            elif animation_type == "fromleft":
                await hyprctl(f"movewindowpixel -{offset} 0,{addr}")
            elif animation_type == "fromright":
                await hyprctl(f"movewindowpixel {offset} 0,{addr}")

            if uid in self.transitioning_scratches:
                return  # abort sequence
            await asyncio.sleep(0.2)  # await for animation to finish

        if uid not in self.transitioning_scratches:
            await hyprctl(f"movetoworkspacesilent special:scratch_{uid},{addr}")

        if (
            animation_type and uid in self.focused_window_tracking
        ):  # focus got lost when animating
            if not autohide:
                await hyprctl(
                    f"focuswindow address:{self.focused_window_tracking[uid]['address']}"
                )

    async def run_show(self, uid, force=False) -> None:
        """<name> shows scratchpad "name" """
        uid = uid.strip()
        item = self.scratches.get(uid)

        self.focused_window_tracking[uid] = await hyprctlJSON("activewindow")

        if not item:
            print(f"{uid} is not configured")
            return

        if item.visible and not force:
            print(f"{uid} is already visible")
            return

        if not item.isAlive():
            print(f"{uid} is not running, restarting...")
            self.procs[uid].kill()
            if item.pid in self.scratches_by_pid:
                del self.scratches_by_pid[item.pid]
            if item.address in self.scratches_by_address:
                del self.scratches_by_address[item.address]
            self.start_scratch_command(uid)
            while uid in self._respawned_scratches:
                await asyncio.sleep(0.05)

        item.visible = True
        monitor = await get_focused_monitor_props()
        assert monitor

        await self.updateScratchInfo(item)

        addr = "address:0x" + item.address

        animation_type = item.conf.get("animation", "").lower()

        wrkspc = monitor["activeWorkspace"]["id"]

        self.transitioning_scratches.add(uid)
        await hyprctl(f"moveworkspacetomonitor special:scratch_{uid} {monitor['name']}")
        await hyprctl(f"movetoworkspacesilent {wrkspc},{addr}")
        if animation_type:
            margin = item.conf.get("margin", DEFAULT_MARGIN)
            fn = getattr(Animations, animation_type)
            await fn(monitor, item.clientInfo, addr, margin)

        await hyprctl(f"focuswindow {addr}")
        await asyncio.sleep(0.2)  # ensure some time for events to propagate
        self.transitioning_scratches.discard(uid)
