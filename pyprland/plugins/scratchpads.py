" Scratchpads addon "
import os
import time
import logging
import asyncio
from typing import Any, cast, Callable
from functools import partial
from collections import defaultdict

from aiofiles import os as aios
from aiofiles import open as aiopen

from ..ipc import notify_error, get_client_props, get_focused_monitor_props
from .interface import Plugin
from ..common import state, get_boolean_function

DEFAULT_MARGIN = 60  # in pixels
AFTER_SHOW_INHIBITION = 0.2  # 200ms of ignorance after a show
DEFAULT_HYSTERESIS = 0.4  # In seconds

# Helper functions {{{

invert_dimension = {"width": "height", "height": "width"}


def get_space_identifier(obj):
    "Returns a unique object for the workspace + monitor combination"
    return (obj.workspace, obj.monitor)


def convert_coords(logger, coords, monitor):
    """
    Converts a string like "X Y" to coordinates relative to monitor
    Supported formats for X, Y:
    - Percentage: "V%". V in [0; 100]
    - Pixels: "Vpx". V should fit in your screen and not be zero

    Example:
    "10% 20%", monitor 800x600 => 80, 120
    """

    assert coords, "coords must be non null"

    def convert(size, dimension):
        scale = float(monitor["scale"])
        if monitor["transform"] in (1, 3):
            dimension = invert_dimension[dimension]
        if size[-1] == "%":
            p = int(size[:-1])
            if p < 0 or p > 100:
                raise ValueError(f"Percentage must be in range [0; 100], got {p}")
            return int(monitor[dimension] / scale * p / 100)
        if size[-2:] == "px":
            return int(size[:-2])
        raise ValueError(
            f"Unsupported format for dimension {dimension} size, got {size}"
        )

    try:
        x_str, y_str = coords.split()

        return convert(x_str, "width"), convert(y_str, "height")
    except Exception as e:
        logger.error(f"Failed to read coordinates: {e}")
        raise e


# }}}


class Animations:  # {{{
    "Animation store"

    @staticmethod
    def fromtop(monitor, client, client_uid, margin):
        "Slide from/to top"
        scale = float(monitor["scale"])
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width = int(monitor["width"] / scale)

        client_width = client["size"][0]
        margin_x = int((mon_width - client_width) / 2) + mon_x

        return f"movewindowpixel exact {margin_x} {mon_y + margin},{client_uid}"

    @staticmethod
    def frombottom(monitor, client, client_uid, margin):
        "Slide from/to bottom"
        scale = float(monitor["scale"])
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width = int(monitor["width"] / scale)
        mon_height = int(monitor["height"] / scale)

        client_width = client["size"][0]
        client_height = client["size"][1]
        margin_x = int((mon_width - client_width) / 2) + mon_x
        return f"movewindowpixel exact {margin_x} {mon_y + mon_height - client_height - margin},{client_uid}"

    @staticmethod
    def fromleft(monitor, client, client_uid, margin):
        "Slide from/to left"
        scale = float(monitor["scale"])
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_height = int(monitor["height"] / scale)

        client_height = client["size"][1]
        margin_y = int((mon_height - client_height) / 2) + mon_y

        return f"movewindowpixel exact {margin + mon_x} {margin_y},{client_uid}"

    @staticmethod
    def fromright(monitor, client, client_uid, margin):
        "Slide from/to right"
        scale = float(monitor["scale"])
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width = int(monitor["width"] / scale)
        mon_height = int(monitor["height"] / scale)

        client_width = client["size"][0]
        client_height = client["size"][1]
        margin_y = int((mon_height - client_height) / 2) + mon_y
        return f"movewindowpixel exact {mon_width - client_width - margin + mon_x } {margin_y},{client_uid}"


# }}}


class Scratch:  # {{{
    "A scratchpad state including configuration & client state"
    log = logging.getLogger("scratch")
    cast_bool: Callable
    get_client_props: Callable

    def __init__(self, uid, opts):
        self.uid = uid
        self.pid = 0
        self.conf = opts
        if not opts.get("process_tracking", True):
            self.conf["lazy"] = True
            self.conf["class_match"] = True
        self.visible = False
        self.client_info = {}
        self.should_hide = False
        self.initialized = False
        self.meta = {}
        self.space_identifier = None
        self.monitor = ""

    async def initialize(self, ex):
        "Initialize the scratchpad"
        if self.initialized:
            return
        self.initialized = True
        await self.updateClientInfo()
        await ex.hyprctl(
            f"movetoworkspacesilent special:scratch_{self.uid},address:{self.full_address}"
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
            if getattr(self, "bogus_pid", False):
                return bool(await self.get_client_props(cls=self.conf["class"]))
            return False

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

    @property
    def full_address(self) -> str:
        "Returns the client address"
        return cast(str, self.client_info.get("address", ""))

    async def updateClientInfo(self, client_info=None) -> None:
        "update the internal client info property, if not provided, refresh based on the current address"
        if client_info is None:
            client_info = await self.get_client_props(addr=self.full_address)
        if not isinstance(client_info, dict):
            self.log.error(
                "client_info of %s must be a dict: %s", self.address, client_info
            )
            raise AssertionError(f"Not a dict: {client_info}")

        self.client_info.update(client_info)

    def __str__(self):
        return f"{self.uid} {self.address} : {self.client_info} / {self.conf}"


# }}}


class ScratchDB:  # {{{
    """Single storage for every Scratch allowing a boring lookup & update API"""

    _by_addr: dict[str, Scratch] = {}
    _by_pid: dict[int, Scratch] = {}
    _by_name: dict[str, Scratch] = {}
    _states: defaultdict[str, set[Scratch]] = defaultdict(set)

    # State management {{{
    def getByState(self, status: str):
        "get a set of `Scratch` being in `status`"
        return self._states[status]

    def hasState(self, scratch: Scratch, status: str):
        "Returns true if `scratch` has state `status`"
        return scratch in self._states[status]

    def setState(self, scratch: Scratch, status: str):
        "Sets `scratch` in the provided status"
        self._states[status].add(scratch)

    def clearState(self, scratch: Scratch, status: str):
        "Unsets the the provided status from the scratch"
        self._states[status].remove(scratch)

    # }}}

    # dict-like {{{
    def __iter__(self):
        "return all Scratch name"
        return iter(self._by_name.keys())

    def values(self):
        "returns every Scratch"
        return self._by_name.values()

    def items(self):
        "return an iterable list of (name, Scratch)"
        return self._by_name.items()

    # }}}

    def reset(self, scratch: Scratch):
        "clears registered address & pid"
        if scratch.address in self._by_addr:
            del self._by_addr[scratch.address]
        if scratch.pid in self._by_pid:
            del self._by_pid[scratch.pid]

    def clear(self, name=None, pid=None, addr=None):
        "clears the index by name, pid or address"
        # {{{

        assert any((name, pid, addr))
        if name is not None and name in self._by_name:
            del self._by_name[name]
        if pid is not None and pid in self._by_pid:
            del self._by_pid[pid]
        if addr is not None and addr in self._by_addr:
            del self._by_addr[addr]
        # }}}

    def register(self, scratch: Scratch, name=None, pid=None, addr=None):
        "set the Scratch index by name, pid or address, or update every index of only `scratch` is provided"
        # {{{
        if not any((name, pid, addr)):
            self._by_name[scratch.uid] = scratch
            self._by_pid[scratch.pid] = scratch
            self._by_addr[scratch.address] = scratch
        else:
            if name is not None:
                d: dict[Any, Scratch] = cast(dict[str, Scratch], self._by_name)
                v = name
            elif pid is not None:
                d = self._by_pid
                v = pid
            elif addr is not None:
                d = self._by_addr
                v = addr
            d[v] = scratch
        # }}}

    def get(self, name=None, pid=None, addr=None) -> Scratch | None:
        "return the Scratch matching given name, pid or address"
        # {{{
        assert 1 == len(list(filter(bool, (name, pid, addr)))), (
            name,
            pid,
            addr,
        )
        if name is not None:
            d: dict[Any, Scratch] = self._by_name
            v = name
        elif pid is not None:
            d = self._by_pid
            v = pid
        elif addr is not None:
            d = self._by_addr
            v = addr
        return d.get(v)
        # }}}


# }}}


class Extension(Plugin):  # pylint: disable=missing-class-docstring {{{
    procs: dict[str, asyncio.subprocess.Process] = {}  # pylint: disable=no-member
    scratches = ScratchDB()

    focused_window_tracking: dict[str, str] = {}

    workspace = ""  # Currently active workspace
    monitor = ""  # Currently active monitor

    _hysteresis_tasks: dict[str, asyncio.Task]  # non-blocking tasks

    cast_bool: Callable

    def __init__(self, name):
        super().__init__(name)
        self._hysteresis_tasks = {}
        self.get_client_props = partial(get_client_props, logger=self.log)
        Scratch.get_client_props = self.get_client_props
        self.get_focused_monitor_props = partial(
            get_focused_monitor_props, logger=self.log
        )

    async def init(self):
        self.cast_bool = get_boolean_function(self.log)
        Scratch.cast_bool = self.cast_bool

    async def exit(self) -> None:
        "exit hook"

        async def die_in_piece(scratch: Scratch):
            if scratch.uid in self.procs:
                proc = self.procs[scratch.uid]
                proc.terminate()
                for _ in range(10):
                    if not await scratch.isAlive():
                        break
                    await asyncio.sleep(0.1)
                if await scratch.isAlive():
                    proc.kill()
                await proc.wait()

        await asyncio.gather(
            *(die_in_piece(scratch) for scratch in self.scratches.values())
        )

    async def on_reload(self) -> None:
        "config loader"
        scratches = {
            name: Scratch(name, options) for name, options in self.config.items()
        }

        scratches_to_spawn = set()
        for name in scratches:
            scratch = self.scratches.get(name)
            if scratch:
                scratch.conf = scratches[name].conf
            else:
                self.scratches.register(scratches[name], name)
                is_lazy = self.cast_bool(scratches[name].conf.get("lazy"), False)
                if not is_lazy:
                    scratches_to_spawn.add(name)

        for name in scratches_to_spawn:
            if await self.ensure_alive(name):
                scratch = self.scratches.get(name)
                assert scratch
                scratch.should_hide = True
            else:
                self.log.error("Failure starting %s", name)

        for scratch in list(self.scratches.getByState("configured")):
            assert scratch
            self.scratches.clearState(scratch, "configured")

    async def _configure_windowrules(self, scratch):
        "Setting up initial client window state (sets windowrules)"
        configured = self.scratches.hasState(scratch, "configured")
        if configured:
            return
        self.scratches.setState(scratch, "configured")
        animation_type: str = scratch.conf.get("animation", "fromTop").lower()
        defined_class: str = scratch.conf.get("class", "")
        if animation_type and defined_class:
            monitor = await get_focused_monitor_props(self.log)
            width, height = convert_coords(
                self.log, scratch.conf.get("size", "80% 80%"), monitor
            )

            position = scratch.conf.get("position")
            if position:
                margin_x, margin_y = convert_coords(self.log, position, monitor)
            else:
                margin_x = (monitor["width"] - width) // 2
                margin_y = (monitor["height"] - height) // 2

            t_pos = {
                "fromtop": f"{margin_x} -200%",
                "frombottom": f"{margin_x} 200%",
                "fromright": f"200% {margin_y}",
                "fromleft": f"-200% {margin_y}",
            }[animation_type]

            await self.hyprctl(
                [
                    f"windowrule workspace special:scratch_{scratch.uid} silent,^({defined_class})$",
                    f"windowrule float,^({defined_class})$",
                    f"windowrule move {t_pos},^({defined_class})$",
                    f"windowrule size {width} {height},^({defined_class})$",
                ],
                "keyword",
            )

    async def __wait_for_client(self, item, use_proc=True) -> bool:
        """Waits for a client to be up and running
        if `class_match` is enabled, will use the class, else the process's PID will be used.
        """
        self.log.info("==> Wait for %s spawning", item.uid)
        for loop_count in range(1, 8):
            await asyncio.sleep(loop_count**2 / 10.0)
            is_alive = await item.isAlive()

            # skips the checks if the process isn't started (just wait)
            if is_alive or not use_proc:
                if self.cast_bool(item.conf.get("class_match")):
                    info = await self.get_client_props(cls=item.conf.get("class"))
                else:
                    info = await self.get_client_props(pid=item.pid)
                if info:
                    await item.updateClientInfo(info)
                    self.log.info(
                        "=> %s client (proc:%s, addr:%s) detected on time",
                        item.uid,
                        item.pid,
                        item.full_address,
                    )
                    self.scratches.register(item)
                    self.scratches.clearState(item, "respawned")
                    return True
            if use_proc and not is_alive:
                return False
        return False

    async def _start_scratch_classbased(self, item) -> bool:
        "Ensure alive, PWA version"
        uid = item.uid
        started = getattr(item, "bogus_pid", False)
        if not await item.isAlive():
            started = False
        if not started:
            self.scratches.reset(item)
            await self.start_scratch_command(uid)
            r = await self.__wait_for_client(item, use_proc=False)
            item.bogus_pid = True
            return r
        return True

    async def _start_scratch(self, item):
        "Ensure alive, standard version"
        uid = item.uid
        if uid in self.procs:
            try:
                self.procs[uid].kill()
            except ProcessLookupError:
                pass
        self.scratches.reset(item)
        await self.start_scratch_command(uid)
        self.log.info("starting %s", uid)
        if not await self.__wait_for_client(item):
            self.log.error("⚠ Failed spawning %s as proc %s", uid, item.pid)
            if await item.isAlive():
                error = "The command didn't open a window"
            else:
                await self.procs[uid].communicate()
                code = self.procs[uid].returncode
                if code:
                    error = f"The command failed with code {code}"
                else:
                    error = "The command terminated sucessfully, is it already running?"
            self.log.error('"%s": %s', item.conf["command"], error)
            await notify_error(error)
            return False
        return True

    async def ensure_alive(self, uid):
        """Ensure the scratchpad is started
        Returns true if started
        """
        item = self.scratches.get(name=uid)
        await self._configure_windowrules(item)
        assert item

        if self.cast_bool(item.conf.get("process_tracking"), True):
            if not await item.isAlive():
                self.log.info("%s is not running, starting...", uid)
                if not await self._start_scratch(item):
                    await notify_error(f'Failed to show scratch "{item.uid}"')
                    return False
            return True

        return await self._start_scratch_classbased(item)

    async def start_scratch_command(self, name: str) -> None:
        "spawns a given scratchpad's process"
        scratch = self.scratches.get(name)
        assert scratch
        self.scratches.setState(scratch, "respawned")
        old_pid = self.procs[name].pid if name in self.procs else 0
        proc = await asyncio.create_subprocess_shell(scratch.conf["command"])
        self.procs[name] = proc
        pid = proc.pid
        scratch.reset(pid)
        self.scratches.register(scratch, pid=pid)
        self.log.info(
            "scratch %s (%s) has pid %s", scratch.uid, scratch.conf.get("command"), pid
        )
        if old_pid:
            self.scratches.clear(pid=old_pid)

    async def updateScratchInfo(self, orig_scratch: Scratch | None = None) -> None:
        """Update every scratchpads information if no `scratch` given,
        else update a specific scratchpad info"""
        pid = orig_scratch.pid if orig_scratch else None
        for client in await self.hyprctlJSON("clients"):
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
            self.log.info("Didn't update scratch info %s", self)

    # Events {{{
    async def event_monitorremoved(self, monitor_name) -> None:
        "Hides scratchpads on the removed screen"
        for scratch in self.scratches.values():
            if scratch.monitor == monitor_name:
                await self.run_hide(scratch.uid, autohide=True)

    async def event_configreloaded(self, _nothing):
        "Re-apply windowrules when hyprland is restarted"
        for scratch in list(self.scratches.getByState("configured")):
            self.scratches.clearState(scratch, "configured")
            await self._configure_windowrules(scratch)

    async def event_activewindowv2(self, addr) -> None:
        "active windows hook"
        for uid, scratch in self.scratches.items():
            if not scratch.client_info:
                continue
            if scratch.address == addr:
                task = self._hysteresis_tasks.get(scratch.uid)
                if task:
                    task.cancel()
                    if scratch.uid in self._hysteresis_tasks:
                        del self._hysteresis_tasks[scratch.uid]
                    self.log.debug("Canceled previous task for %s", uid)
            else:
                if (
                    scratch.visible
                    and scratch.conf.get("unfocus") == "hide"
                    and not self.scratches.hasState(scratch, "transition")
                ):
                    last_shown = scratch.meta.get("last_shown", 0)
                    if last_shown + AFTER_SHOW_INHIBITION > time.time():
                        self.log.debug(
                            "(SKIPPED) hide %s because another client is active",
                            uid,
                        )
                        continue

                    hysteresis = scratch.conf.get("hysteresis", DEFAULT_HYSTERESIS)
                    if hysteresis:
                        task = self._hysteresis_tasks.get(scratch.uid)
                        if task:
                            task.cancel()
                            self.log.debug("Canceled previous task for %s", uid)
                        self._hysteresis_tasks[scratch.uid] = asyncio.create_task(
                            asyncio.sleep(hysteresis)
                        )

                        async def _task(scratch, uid):
                            await self._hysteresis_tasks[scratch.uid]
                            del self._hysteresis_tasks[scratch.uid]
                            if state.active_window == scratch.full_address:
                                self.log.debug(
                                    "Skipped hidding %s because client got the focus back",
                                    uid,
                                )
                                return
                            self.log.debug(
                                "hide %s because another client is active", uid
                            )
                            await self.run_hide(uid, autohide=True)

                        asyncio.create_task(_task(scratch, uid))
                    else:
                        self.log.debug("hide %s because another client is active", uid)
                        await self.run_hide(uid, autohide=True)

    async def _alternative_lookup(self):
        "if class_match attribute is defined, use class matching and return True"
        class_lookup_hack = [
            s
            for s in self.scratches.getByState("respawned")
            if self.cast_bool(s.conf.get("class_match"))
        ]
        if not class_lookup_hack:
            return False
        self.log.debug("Lookup hack triggered")
        # hack to update the client info from the provided class
        for client in await self.hyprctlJSON("clients"):
            assert isinstance(client, dict)
            for pending_scratch in class_lookup_hack:
                if pending_scratch.conf["class"] == client["class"]:
                    self.scratches.register(pending_scratch, addr=client["address"][2:])
                    self.log.debug("client class found: %s", client)
                    await pending_scratch.updateClientInfo(client)
        return True

    async def event_openwindow(self, params) -> None:
        "open windows hook"
        addr, _wrkspc, _kls, _title = params.split(",", 3)
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
            await item.initialize(self)

    # }}}
    # Commands {{{
    async def run_toggle(self, uid_or_uids: str) -> None:
        """<name> toggles visibility of scratchpad "name" """
        if " " in uid_or_uids:
            uids = [x.strip() for x in uid_or_uids.split() if x.strip()]
        else:
            uids = [uid_or_uids.strip()]

        assert len(uids)
        first_scratch = self.scratches.get(uids[0])
        if not first_scratch:
            self.log.warning("%s doesn't exist, can't toggle.", uids[0])
            await notify_error(
                f"Scratchpad '{uids[0]}' not found, check your configuration or the toggle parameter"
            )
            return

        is_visible = (
            first_scratch.visible
            and first_scratch.space_identifier == get_space_identifier(self)
        )

        tasks = []

        for uid in uids:
            item = self.scratches.get(uid)
            if not item:
                self.log.warning("%s is not configured", uid)
            else:
                self.log.debug("%s is visible = %s", uid, item.visible)
                if is_visible and await item.isAlive():
                    tasks.append(partial(self.run_hide, uid))
                else:
                    tasks.append(partial(self.run_show, uid))
        await asyncio.gather(*(asyncio.create_task(t()) for t in tasks))

    async def _anim_hide(self, animation_type, scratch):
        "animate hiding a scratchpad"
        offset = scratch.conf.get("offset")
        if offset is None:
            if "size" not in scratch.client_info:
                await self.updateScratchInfo(scratch)

            offset = int(1.3 * scratch.client_info["size"][1])

        addr = "address:" + scratch.full_address
        if animation_type == "fromtop":
            await self.hyprctl(f"movewindowpixel 0 -{offset},{addr}")
        elif animation_type == "frombottom":
            await self.hyprctl(f"movewindowpixel 0 {offset},{addr}")
        elif animation_type == "fromleft":
            await self.hyprctl(f"movewindowpixel -{offset} 0,{addr}")
        elif animation_type == "fromright":
            await self.hyprctl(f"movewindowpixel {offset} 0,{addr}")

        if self.scratches.hasState(scratch, "transition"):
            return  # abort sequence
        await asyncio.sleep(0.2)  # await for animation to finish

    async def run_show(self, uid) -> None:
        """<name> shows scratchpad "name" """
        item = self.scratches.get(uid)

        if not item:
            self.log.warning("%s doesn't exist, can't hide.", uid)
            await notify_error(
                f"Scratchpad '{uid}' not found, check your configuration or the show parameter"
            )
            return

        self.focused_window_tracking[uid] = state.active_window

        if not item:
            self.log.warning("%s is not configured", uid)
            return

        self.log.info("Showing %s", uid)
        if not await self.ensure_alive(uid):
            self.log.error("Failed to show %s, aborting.", uid)
            return

        excluded = item.conf.get("excludes", [])
        if excluded == "*":
            excluded = [
                scratch.uid for scratch in self.scratches.values() if scratch.uid != uid
            ]
        for e_uid in excluded:
            scratch = self.scratches.get(e_uid)
            assert scratch
            if scratch.visible:
                await self.run_hide(e_uid, autohide=True)
        await item.updateClientInfo()
        await item.initialize(self)

        item.visible = True
        item.space_identifier = get_space_identifier(self)
        monitor = await get_focused_monitor_props(self.log)
        assert monitor
        assert item.full_address, "No address !"

        animation_type = item.conf.get("animation", "").lower()
        wrkspc = monitor["activeWorkspace"]["id"]

        self.scratches.setState(item, "transition")
        item.monitor = monitor["name"]
        # Start the transition
        await self.hyprctl(
            [
                f"moveworkspacetomonitor special:scratch_{uid} {item.monitor}",
                f"movetoworkspacesilent {wrkspc},address:{item.full_address}",
                f"alterzorder top,address:{item.full_address}",
            ]
        )
        await self._fix_size_and_position(item, monitor)
        if animation_type:
            margin = item.conf.get("margin", DEFAULT_MARGIN)
            fn = getattr(Animations, animation_type)
            command = fn(
                monitor, item.client_info, "address:" + item.full_address, margin
            )
            await self.hyprctl(command)

        await self.hyprctl(f"focuswindow address:{item.full_address}")
        await asyncio.sleep(0.2)  # ensure some time for events to propagate
        # Transition ended
        self.scratches.clearState(item, "transition")
        item.meta["last_shown"] = time.time()

    async def _fix_size_and_position(self, item, monitor):
        "fixes the size and position of the scratchpad"

        size = item.conf.get("size")
        position = item.conf.get("position")
        if position:
            x_pos, y_pos = convert_coords(self.log, position, monitor)
            x_pos_abs, y_pos_abs = x_pos + monitor["x"], y_pos + monitor["y"]
            await self.hyprctl(
                f"movewindowpixel exact {x_pos_abs} {y_pos_abs},address:{item.full_address}"
            )
        if size:
            width, height = convert_coords(self.log, size, monitor)
            max_size = item.conf.get("max_size")
            if max_size:
                max_width, max_height = convert_coords(self.log, max_size, monitor)
                width = min(max_width, width)
                height = min(max_height, height)
            await self.hyprctl(
                f"resizewindowpixel exact {width} {height},address:{item.full_address}"
            )
        if size or position:
            await item.updateClientInfo()

    async def run_hide(self, uid: str, force=False, autohide=False) -> None:
        """<name> hides scratchpad "name"
        if `autohide` is True, skips focus tracking
        `force` ignores the visibility check"""
        scratch = self.scratches.get(uid)

        if not scratch:
            await notify_error(
                f"Scratchpad '{uid}' not found, check your configuration or the hide parameter"
            )
            self.log.warning("%s is not configured", uid)
            return
        if not scratch.visible and not force and not autohide:
            await notify_error(f"Scratchpad '{uid}' is not visible, will not hide.")
            self.log.warning("%s is already hidden", uid)
            return
        scratch.visible = False
        self.log.info("Hiding %s", uid)
        animation_type: str = scratch.conf.get("animation", "").lower()
        if animation_type:
            await self._anim_hide(animation_type, scratch)

        if not self.scratches.hasState(scratch, "transition"):
            await self.hyprctl(
                f"movetoworkspacesilent special:scratch_{uid},address:{scratch.full_address}"
            )

        if (
            not autohide
            and animation_type
            and uid in self.focused_window_tracking
            and self.cast_bool(scratch.conf.get("restore_focus"), True)
        ):  # focus got lost when animating
            await self.hyprctl(
                f"focuswindow address:{self.focused_window_tracking[uid]}"
            )
            del self.focused_window_tracking[uid]

    # }}}


# }}}
