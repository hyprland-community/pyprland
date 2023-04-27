import subprocess
import asyncio
from ..ipc import (
    hyprctl,
    hyprctlJSON,
    get_focused_monitor_props,
)
import os

from .interface import Plugin

DEFAULT_MARGIN = 60


async def get_client_props_by_pid(pid: int):
    for client in await hyprctlJSON("clients"):
        assert isinstance(client, dict)
        if client.get("pid") == pid:
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
        mon_y = monitor["y"]
        mon_height = monitor["height"]

        client_height = client["size"][1]
        margin_y = int((mon_height - client_height) / 2) + mon_y

        await hyprctl(f"movewindowpixel exact {margin} {margin_y},{client_uid}")

    @classmethod
    async def fromright(cls, monitor, client, client_uid, margin):
        mon_y = monitor["y"]
        mon_width = monitor["width"]
        mon_height = monitor["height"]

        client_width = client["size"][0]
        client_height = client["size"][1]
        margin_y = int((mon_height - client_height) / 2) + mon_y
        await hyprctl(
            f"movewindowpixel exact {mon_width - client_width - margin} {margin_y},{client_uid}"
        )


class Scratch:
    def __init__(self, uid, opts):
        self.uid = uid
        self.pid = 0
        self.conf = opts
        self.visible = False
        self.just_created = True
        self.clientInfo = {}

    def isAlive(self):
        path = f"/proc/{self.pid}"
        if os.path.exists(path):
            for line in open(os.path.join(path, "status"), "r").readlines():
                if line.startswith("State"):
                    state = line.split()[1]
                    return state in "RSDTt"  # not "Z (zombie)"or "X (dead)"
        return False

    def reset(self, pid: int):
        self.pid = pid
        self.visible = False
        self.just_created = True
        self.clientInfo = {}

    @property
    def address(self) -> str:
        return str(self.clientInfo.get("address", ""))[2:]

    async def updateClientInfo(self, clientInfo=None):
        if clientInfo is None:
            clientInfo = await get_client_props_by_pid(self.pid)
        assert isinstance(clientInfo, dict)
        self.clientInfo.update(clientInfo)


class Extension(Plugin):
    async def init(self):
        self.procs: dict[str, subprocess.Popen] = {}
        self.scratches: dict[str, Scratch] = {}
        self.transitioning_scratches: set[str] = set()
        self._respawned_scratches: set[str] = set()
        self.scratches_by_address: dict[str, Scratch] = {}
        self.scratches_by_pid: dict[int, Scratch] = {}

    async def exit(self):
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

    async def load_config(self, config):
        config = config["scratchpads"]
        scratches = {k: Scratch(k, v) for k, v in config.items()}

        is_updating = bool(self.scratches)

        for name in scratches:
            if name not in self.scratches:
                self.scratches[name] = scratches[name]
            else:
                self.scratches[name].conf = scratches[name].conf

        if is_updating:
            await self.exit()

        # not known yet
        for name in self.scratches:
            self.start_scratch_command(name)

    def start_scratch_command(self, name: str):
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
        if old_pid:
            del self.scratches_by_pid[old_pid]

    # Events
    async def event_activewindowv2(self, addr):
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
                        await self.run_hide(uid)

    async def event_openwindow(self, params):
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

    async def run_toggle(self, uid: str):
        uid = uid.strip()
        item = self.scratches.get(uid)
        if not item:
            print(f"{uid} is not configured")
            return
        if item.visible:
            await self.run_hide(uid)
        else:
            await self.run_show(uid)

    async def updateScratchInfo(self, scratch: Scratch | None = None):
        if scratch is None:
            for client in await hyprctlJSON("clients"):
                assert isinstance(client, dict)
                pid = client["pid"]
                assert isinstance(pid, int)
                scratch = self.scratches_by_pid.get(pid)
                if scratch:
                    await scratch.updateClientInfo(client)
                    self.scratches_by_address[
                        scratch.clientInfo["address"][2:]
                    ] = scratch
        else:
            add_to_address_book = ("address" not in scratch.clientInfo) or (
                scratch.address not in self.scratches_by_address
            )
            await scratch.updateClientInfo()
            if add_to_address_book:
                self.scratches_by_address[scratch.clientInfo["address"][2:]] = scratch

    async def run_hide(self, uid: str, force=False):
        uid = uid.strip()
        item = self.scratches.get(uid)
        if not item:
            print(f"{uid} is not configured")
            return
        if not item.visible and not force:
            print(f"{uid} is already hidden")
            return
        item.visible = False
        pid = "pid:%d" % item.pid
        animation_type = item.conf.get("animation", "").lower()
        if animation_type:
            offset = item.conf.get("offset")
            if offset is None:
                if "size" not in item.clientInfo:
                    await self.updateScratchInfo(item)

                offset = int(1.3 * item.clientInfo["size"][1])

            if animation_type == "fromtop":
                await hyprctl(f"movewindowpixel 0 -{offset},{pid}")
            elif animation_type == "frombottom":
                await hyprctl(f"movewindowpixel 0 {offset},{pid}")
            elif animation_type == "fromleft":
                await hyprctl(f"movewindowpixel -{offset} 0,{pid}")
            elif animation_type == "fromright":
                await hyprctl(f"movewindowpixel {offset} 0,{pid}")

            if uid in self.transitioning_scratches:
                return  # abort sequence
            await asyncio.sleep(0.2)  # await for animation to finish
        if uid not in self.transitioning_scratches:
            await hyprctl(f"movetoworkspacesilent special:scratch,{pid}")

    async def run_show(self, uid, force=False):
        uid = uid.strip()
        item = self.scratches.get(uid)

        if not item:
            print(f"{uid} is not configured")
            return

        if item.visible and not force:
            print(f"{uid} is already visible")
            return

        if not item.isAlive():
            print(f"{uid} is not running, restarting...")
            self.procs[uid].kill()
            self.start_scratch_command(uid)
            while uid in self._respawned_scratches:
                await asyncio.sleep(0.05)

        item.visible = True
        monitor = await get_focused_monitor_props()
        assert monitor

        await self.updateScratchInfo(item)

        pid = "pid:%d" % item.pid

        animation_type = item.conf.get("animation", "").lower()

        wrkspc = monitor["activeWorkspace"]["id"]
        self.transitioning_scratches.add(uid)
        await hyprctl(f"movetoworkspacesilent {wrkspc},{pid}")
        if animation_type:
            margin = item.conf.get("margin", DEFAULT_MARGIN)
            fn = getattr(Animations, animation_type)
            await fn(monitor, item.clientInfo, pid, margin)

        await hyprctl(f"focuswindow {pid}")
        await asyncio.sleep(0.2)  # ensure some time for events to propagate
        self.transitioning_scratches.discard(uid)
