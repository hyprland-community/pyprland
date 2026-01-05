"""Scratchpads addon."""

import asyncio
import contextlib
import time
from collections.abc import Iterable
from functools import partial
from typing import cast

from ...adapters.units import convert_coords, convert_monitor_dimension
from ...common import MINIMUM_ADDR_LEN, SharedState, apply_variables, is_rotated
from ...ipc import get_client_props, get_monitor_props, notify_error
from ...types import ClientInfo, MonitorInfo, VersionInfo
from ..interface import Plugin
from .animations import AnimationTarget, Placement
from .common import FocusTracker, HideFlavors
from .helpers import (
    apply_offset,
    compute_offset,
    get_active_space_identifier,
    get_all_space_identifiers,
    get_match_fn,
    mk_scratch_name,
)
from .lookup import ScratchDB
from .objects import Scratch

AFTER_SHOW_INHIBITION = 0.3  # 300ms of ignorance after a show
DEFAULT_MARGIN = 60  # in pixels
DEFAULT_HIDE_DELAY = 0  # in seconds
DEFAULT_HYSTERESIS = 0.4  # in seconds


# Ad-hoc classes & functions {{{
class WindowRuleSet:
    """Windowrule set builder."""

    def __init__(self, state: SharedState) -> None:
        self.state = state
        self._params: list[tuple[str, str]] = []
        self._class = ""
        self._name = "PyprScratchR"

    def set_class(self, value: str) -> None:
        """Set the windowrule matching class."""
        self._class = value

    def set_name(self, value: str) -> None:
        """Set the windowrule name."""
        self._name = value

    def set(self, param: str, value: str) -> None:
        """Set a windowrule property."""
        self._params.append((param, value))

    def _get_content(self) -> Iterable[str]:
        """Get the windowrule content."""
        if self.state.hyprland_version > VersionInfo(0, 47, 2):
            if self.state.hyprland_version < VersionInfo(0, 53, 0):
                for p in self._params:
                    yield f"windowrule {p[0]} {p[1]}, class: {self._class}"
            elif self._name:
                yield f"windowrule[{self._name}]:enable true"
                yield f"windowrule[{self._name}]:match:class {self._class}"
                for p in self._params:
                    yield f"windowrule[{self._name}]:{p[0]} {p[1]}"
            else:
                for p in self._params:
                    yield f"windowrule {p[0]} {p[1]}, match:class {self._class}"
        else:
            for p in self._params:
                yield f"windowrule {p[0]} {p[1]}, ^({self._class})$"

    def get_content(self) -> list[str]:
        """Get the windowrule content."""
        return list(self._get_content())


def get_animation_type(scratch: Scratch) -> str:
    """Get the animation type or an empty string if not set."""
    return scratch.conf.get_str("animation", "").lower()


# }}}


class Extension(Plugin):  # pylint: disable=missing-class-docstring {{{
    """Scratchpads addon."""

    procs: dict[str, asyncio.subprocess.Process] = {}  # pylint: disable=no-member
    scratches = ScratchDB()

    workspace = ""  # Currently active workspace
    monitor = ""  # Currently active monitor

    _hysteresis_tasks: dict[str, asyncio.Task]  # non-blocking tasks
    focused_window_tracking: dict[str, FocusTracker] = {}
    previously_focused_window: str = ""
    last_focused: Scratch | None = None

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._hysteresis_tasks = {}
        self.get_client_props = staticmethod(partial(get_client_props, logger=self.log))
        Scratch.get_client_props = self.get_client_props
        self.get_monitor_props = staticmethod(partial(get_monitor_props, logger=self.log))

    async def exit(self) -> None:
        """Exit hook."""

        async def die_in_piece(scratch: Scratch) -> None:
            if scratch.uid in self.procs:
                proc = self.procs[scratch.uid]

                try:
                    proc.terminate()
                except ProcessLookupError:
                    pass
                else:
                    for _ in range(10):
                        if not await scratch.is_alive():
                            break
                        await asyncio.sleep(0.1)
                    if await scratch.is_alive():
                        with contextlib.suppress(ProcessLookupError):
                            proc.kill()
                await proc.wait()

        await asyncio.gather(*(die_in_piece(scratch) for scratch in self.scratches.values()))

    async def on_reload(self) -> None:
        """Config loader."""
        # Sanity checks
        _scratch_classes: dict[str, str] = {}
        for uid, scratch in self.config.items():
            _klass = scratch.get("class")
            if _klass:
                if _klass in _scratch_classes:
                    text = "Scratch class %s is duplicated (in %s and %s)"
                    args = (
                        scratch["class"],
                        uid,
                        _scratch_classes[_klass],
                    )
                    self.log.error(text, *args)
                    await self.notify_error(text % args)
                _scratch_classes[_klass] = uid

        # Create new scratches with fresh config items
        scratches = {name: Scratch(name, self.config, self.state) for name, options in self.config.iter_subsections()}

        scratches_to_spawn = set()
        for name, new_scratch in scratches.items():
            scratch = self.scratches.get(name)
            if scratch:  # if existing scratch exists, overrides the conf object
                scratch.set_config(self.config)
            else:
                # else register it
                self.scratches.register(new_scratch, name)
                is_lazy = new_scratch.conf.get_bool("lazy", True)
                if not is_lazy:
                    scratches_to_spawn.add(name)

        for name in scratches_to_spawn:
            if await self.ensure_alive(name):
                scratch = self.scratches.get(name)
                assert scratch
                scratch.meta.should_hide = True
            else:
                self.log.error("Failure starting %s", name)

        for scratch in list(self.scratches.get_by_state("configured")):
            assert scratch
            self.scratches.clear_state(scratch, "configured")

    async def _unset_windowrules(self, scratch: Scratch) -> None:
        """Unset the windowrules."""
        defined_class = scratch.conf.get("class", "")
        if defined_class:
            if self.state.hyprland_version < VersionInfo(0, 53, 0):
                if self.state.hyprland_version > VersionInfo(0, 47, 2):
                    await self.hyprctl(f"windowrule unset, class: {defined_class}", "keyword")
                else:
                    await self.hyprctl(f"windowrule unset, ^({defined_class})$", "keyword")
            else:
                await self.hyprctl(f"windowrule[{scratch.uid}]:enable false", "keyword")

    async def _configure_windowrules(self, scratch: Scratch) -> None:
        """Set initial client window state (sets windowrules)."""
        self.scratches.set_state(scratch, "configured")
        animation_type: str = scratch.conf.get_str("animation", "fromTop").lower()
        defined_class: str = scratch.conf.get_str("class", "")
        skipped_windowrules: list[str] = cast("list", scratch.conf.get("skip_windowrules", []))
        wr = WindowRuleSet(self.state)
        wr.set_class(defined_class)
        wr.set_name(scratch.uid)
        if defined_class:
            forced_monitor = scratch.conf.get("force_monitor")
            if forced_monitor and forced_monitor not in self.state.monitors:
                self.log.error("forced monitor %s doesn't exist", forced_monitor)
                await self.notify_error(f"Monitor '{forced_monitor}' doesn't exist, check {scratch.uid}'s scratch configuration")
                forced_monitor = None
            monitor = await self.get_monitor_props(name=cast("str | None", forced_monitor))
            width, height = convert_coords(scratch.conf.get_str("size", "80% 80%"), monitor)

            if "float" not in skipped_windowrules:
                if self.state.hyprland_version < VersionInfo(0, 53, 0):
                    wr.set("float", "")
                else:
                    wr.set("float", "on")
            if "workspace" not in skipped_windowrules:
                wr.set("workspace", f"{mk_scratch_name(scratch.uid)} silent")
            set_aspect = "aspect" not in skipped_windowrules

            if animation_type:
                margin_x = (monitor["width"] - width) // 2
                margin_y = (monitor["height"] - height) // 2

                if is_rotated(monitor):
                    margin_x, margin_y = margin_y, margin_x

                t_pos = {
                    "fromtop": f"{margin_x} -200%",
                    "frombottom": f"{margin_x} 200%",
                    "fromright": f"200% {margin_y}",
                    "fromleft": f"-200% {margin_y}",
                }[animation_type]
                if set_aspect:
                    wr.set("move", t_pos)

            if set_aspect:
                wr.set("size", f"{width} {height}")

            await self.hyprctl(wr.get_content(), "keyword")

    async def __wait_for_client(self, scratch: Scratch, use_proc: bool = True) -> bool:
        """Wait for a client to be up and running.

        if `match_by=` is used, will use the match criteria, else the process's PID will be used.
        """
        self.log.info("==> Wait for %s spawning", scratch.uid)
        interval_range = [0.1] * 10 + [0.2] * 20 + [0.5] * 15
        for interval in interval_range:
            await asyncio.sleep(interval)
            is_alive = await scratch.is_alive()

            # skips the checks if the process isn't started (just wait)
            if is_alive or not use_proc:
                info = await scratch.fetch_matching_client()
                if info:
                    await scratch.update_client_info(info)
                    self.log.info(
                        "=> %s client (proc:%s, addr:%s) detected on time",
                        scratch.uid,
                        scratch.pid,
                        scratch.full_address,
                    )
                    self.scratches.register(scratch)
                    self.scratches.clear_state(scratch, "respawned")
                    return True
            if use_proc and not is_alive:
                return False
        return False

    async def _start_scratch_nopid(self, scratch: Scratch) -> bool:
        """Ensure alive, PWA version."""
        uid = scratch.uid
        started = scratch.meta.no_pid
        if not await scratch.is_alive():
            started = False
        if not started:
            self.scratches.reset(scratch)
            await self.start_scratch_command(uid)
            r = await self.__wait_for_client(scratch, use_proc=False)
            scratch.meta.no_pid = r
            return r
        return True

    async def _start_scratch(self, scratch: Scratch) -> bool:
        """Ensure alive, standard version."""
        uid = scratch.uid
        if uid in self.procs:
            with contextlib.suppress(ProcessLookupError):
                self.procs[uid].kill()
        self.scratches.reset(scratch)
        await self.start_scratch_command(uid)
        self.log.info("starting %s", uid)
        if not await self.__wait_for_client(scratch):
            self.log.error("⚠ Failed spawning %s as proc %s", uid, scratch.pid)
            if await scratch.is_alive():
                error = "The command didn't open a window"
            else:
                await self.procs[uid].communicate()
                code = self.procs[uid].returncode
                error = f"The command failed with code {code}" if code else "The command terminated successfully, is it already running?"
            self.log.error('"%s": %s', scratch.conf["command"], error)
            await notify_error(error)
            return False
        return True

    async def ensure_alive(self, uid: str) -> bool:
        """Ensure the scratchpad is started.

        Returns true if started
        """
        item = self.scratches.get(name=uid)
        assert item

        if not item.have_command:
            return True

        if item.conf.get_bool("process_tracking", True):
            if not await item.is_alive():
                await self._configure_windowrules(item)
                self.log.info("%s is not running, starting...", uid)
                if not await self._start_scratch(item):
                    await notify_error(f'Failed to show scratch "{item.uid}"')
                    return False
            await self._unset_windowrules(item)
            return True

        return await self._start_scratch_nopid(item)

    async def start_scratch_command(self, name: str) -> None:
        """Spawn a given scratchpad's process."""
        scratch = self.scratches.get(name)
        assert scratch
        self.scratches.set_state(scratch, "respawned")
        old_pid = self.procs[name].pid if name in self.procs else 0
        command = apply_variables(cast("str", scratch.conf["command"]), self.state.variables)
        proc = await asyncio.create_subprocess_shell(command)
        self.procs[name] = proc
        pid = proc.pid
        scratch.reset(pid)
        self.scratches.register(scratch, pid=pid)
        self.log.info("scratch %s (%s) has pid %s", scratch.uid, scratch.conf.get("command"), pid)
        if old_pid:
            self.scratches.clear(pid=old_pid)

    async def update_scratch_info(self, orig_scratch: Scratch | None = None) -> None:
        """Update Scratchpad information.

        If `scratch` is given, update only this scratchpad.
        Else, update every scratchpad.
        """
        pid = orig_scratch.pid if orig_scratch else None
        for client in await self.hyprctl_json("clients"):
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
                await scratch.update_client_info(cast("ClientInfo", client))
                break
        else:
            self.log.info("Didn't update scratch info %s", self)

    # Events {{{

    async def event_changefloatingmode(self, args: str) -> None:
        """Update the floating mode of scratchpads."""
        addr, _onoff = args.split(",")
        onoff = int(_onoff)
        for scratch in self.scratches.values():
            if scratch.address == addr:
                scratch.client_info["floating"] = bool(onoff)

    async def event_workspace(self, name: str) -> None:
        """Workspace hook."""
        for scratch in self.scratches.values():
            scratch.event_workspace(name)

        self.workspace = name

    async def event_closewindow(self, addr: str) -> None:
        """Close window hook."""
        # Removes this address from the extra_addr
        addr = "0x" + addr
        for scratch in self.scratches.values():
            if addr in scratch.extra_addr:
                scratch.extra_addr.remove(addr)
            if addr in scratch.meta.extra_positions:
                del scratch.meta.extra_positions[addr]

    async def event_monitorremoved(self, monitor_name: str) -> None:
        """Hides scratchpads on the removed screen."""
        for scratch in self.scratches.values():
            if scratch.monitor == monitor_name:
                try:
                    await self.run_hide(scratch.uid, flavor=HideFlavors.TRIGGERED_BY_AUTOHIDE)
                except Exception as e:  # pylint: disable=broad-except
                    self.log.exception("Failed to hide %s", scratch.uid)
                    await self.notify_info(f"Failed to hide {scratch.uid}: {e}")

    async def event_activewindowv2(self, addr: str) -> None:
        """Active windows hook."""
        full_address = "" if not addr or len(addr) < MINIMUM_ADDR_LEN else "0x" + addr
        for uid, scratch in self.scratches.items():
            if not scratch.client_info:
                continue  # type: ignore
            if scratch.have_address(full_address):
                self.last_focused = scratch
                self.cancel_task(uid)
            elif scratch.visible and scratch.conf.get("unfocus") == "hide":
                last_shown = scratch.meta.last_shown
                if last_shown + AFTER_SHOW_INHIBITION > time.time():
                    self.log.debug(
                        "(SKIPPED) hide %s because another client is active",
                        uid,
                    )
                    continue

                await self._hysteresis_handling(scratch)
        self.previously_focused_window = full_address

    async def _hysteresis_handling(self, scratch: Scratch) -> None:
        """Hysteresis handling."""
        hysteresis = scratch.conf.get_float("hysteresis", DEFAULT_HYSTERESIS)
        if hysteresis:
            self.cancel_task(scratch.uid)

            async def _task(scratch: Scratch, delay: float) -> None:
                await asyncio.sleep(delay)
                self.log.debug("hide %s because another client is active", scratch.uid)
                await self.run_hide(scratch.uid, flavor=HideFlavors.TRIGGERED_BY_AUTOHIDE)

                with contextlib.suppress(KeyError):
                    del self._hysteresis_tasks[scratch.uid]

            self._hysteresis_tasks[scratch.uid] = asyncio.create_task(_task(scratch, hysteresis))
        else:
            self.log.debug("hide %s because another client is active", scratch.uid)
            await self.run_hide(scratch.uid, flavor=HideFlavors.TRIGGERED_BY_AUTOHIDE)

    async def _alternative_lookup(self) -> bool:
        """If not matching by pid, use specific matching and return True."""
        class_lookup_hack = [s for s in self.scratches.get_by_state("respawned") if s.conf.get("match_by", "pid") != "pid"]
        if not class_lookup_hack:
            return False
        self.log.debug("Lookup hack triggered")
        clients = cast("list[ClientInfo]", await self.hyprctl_json("clients"))
        for pending_scratch in class_lookup_hack:
            match_by, match_value = pending_scratch.get_match_props()
            match_fn = get_match_fn(match_by, match_value)
            for client in clients:
                if match_fn(client[match_by], match_value):  # type: ignore
                    self.scratches.register(pending_scratch, addr=client["address"][2:])
                    self.log.debug("client class found: %s", client)
                    await pending_scratch.update_client_info(client)
        return True

    async def event_openwindow(self, params: str) -> None:
        """Open windows hook."""
        addr, _wrkspc, _kls, _title = params.split(",", 3)
        item = self.scratches.get(addr=addr)
        respawned = list(self.scratches.get_by_state("respawned"))

        if item:
            # Ensure initialized (no-op if already initialized)
            await item.initialize(self)
        elif respawned:
            # NOTE: for windows which aren't related to the process (see #8)
            if not await self._alternative_lookup():
                self.log.info("Updating Scratch info")
                await self.update_scratch_info()
            if item and item.meta.should_hide:
                await self.run_hide(item.uid, flavor=HideFlavors.FORCED)
        else:
            clients = await self.hyprctl_json("clients")
            for item in self.scratches.values():
                if await self._handle_multiwindow(item, clients):
                    return

    # }}}
    def cancel_task(self, uid: str) -> bool:
        """Cancel a task."""
        task = self._hysteresis_tasks.get(uid)
        if task:
            task.cancel()
            self.log.debug("Canceled previous task for %s", uid)
            if uid in self._hysteresis_tasks:
                del self._hysteresis_tasks[uid]
            return True
        return False

    # Commands {{{

    async def run_attach(self) -> None:
        """Attach the focused window to the last focused scratchpad."""
        if not self.last_focused:
            await self.notify_error("No scratchpad was focused")
            return
        focused = self.state.active_window
        scratch = self.last_focused
        if focused == scratch.full_address:
            await self.notify_info("Scratch can't attach to itself")
            return
        if not scratch.visible:
            await self.run_show(scratch.uid)

        if self.state.active_window in scratch.extra_addr:
            scratch.extra_addr.remove(focused)
        else:
            scratch.extra_addr.add(focused)

        if scratch.conf.get("pinned", True):
            await self.hyprctl(f"pin address:{focused}")

    async def run_toggle(self, uid_or_uids: str) -> None:
        """<name> toggles visibility of scratchpad "name" (supports multiple names)."""
        uids = list(filter(bool, map(str.strip, uid_or_uids.split()))) if " " in uid_or_uids else [uid_or_uids.strip()]

        for uid in uids:
            self.cancel_task(uid)

        assert len(uids) > 0
        first_scratch = self.scratches.get(uids[0])
        if not first_scratch:
            self.log.warning("%s doesn't exist, can't toggle.", uids[0])
            await notify_error(f"Scratchpad '{uids[0]}' not found, check your configuration & the toggle parameter")
            return

        self.log.debug(
            "visibility_check: %s == %s",
            first_scratch.meta.space_identifier,
            get_active_space_identifier(self.state),
        )
        if first_scratch.conf.get_bool("alt_toggle"):
            # Needs to be on any monitor (if workspace matches)
            extra_visibility_check = first_scratch.meta.space_identifier in await get_all_space_identifiers(
                await self.hyprctl_json("monitors")
            )
        else:
            # Needs to be on the active monitor+workspace
            extra_visibility_check = first_scratch.meta.space_identifier == get_active_space_identifier(
                self.state
            )  # Visible on the currently focused monitor

        is_visible = first_scratch.visible and (
            first_scratch.forced_monitor or extra_visibility_check
        )  # Always showing on the same monitor
        tasks = []

        for uid in uids:
            item = self.scratches.get(uid)
            if not item:
                self.log.warning("%s is not configured", uid)
            else:
                self.log.debug("%s visibility: %s and %s", uid, is_visible, item.visible)
                if is_visible and await item.is_alive():
                    tasks.append(partial(self.run_hide, uid))
                else:
                    tasks.append(partial(self.run_show, uid))
        await asyncio.gather(*(asyncio.create_task(t()) for t in tasks))

    async def get_offsets(self, scratch: Scratch, monitor: MonitorInfo | None = None) -> tuple[int, int]:
        """Return offset from config or use margin as a ref."""
        offset = scratch.conf.get("offset")
        if monitor is None:
            monitor = await get_monitor_props(self.log, name=scratch.forced_monitor)
        rotated = is_rotated(monitor)
        aspect = reversed(scratch.client_info["size"]) if rotated else scratch.client_info["size"]

        if offset:
            return cast("tuple[int, int]", (convert_monitor_dimension(cast("str", offset), ref, monitor) for ref in aspect))

        mon_size = [monitor["height"], monitor["width"]] if rotated else [monitor["width"], monitor["height"]]

        offsets = [convert_monitor_dimension("100%", dim, monitor) for dim in mon_size]
        return cast("tuple[int, int]", offsets)

    async def _hide_transition(self, scratch: Scratch, monitor: MonitorInfo) -> bool:
        """Animate hiding a scratchpad."""
        animation_type: str = get_animation_type(scratch)

        if not animation_type:
            return False

        await self._slide_animation(animation_type, scratch, await self.get_offsets(scratch, monitor))
        delay: float = scratch.conf.get_float("hide_delay", DEFAULT_HIDE_DELAY)
        if delay:
            await asyncio.sleep(delay)  # await for animation to finish
        return True

    async def _slide_animation(
        self,
        animation_type: str,
        scratch: Scratch,
        offset: tuple[int, int],
        target: AnimationTarget = AnimationTarget.ALL,
    ) -> None:
        """Slides the window `offset` pixels respecting `animation_type`."""
        addresses: list[str] = []
        if target != AnimationTarget.MAIN:
            addresses.extend(scratch.extra_addr)
        if target != AnimationTarget.EXTRA:
            addresses.append(scratch.full_address)
        off_x, off_y = offset

        animation_actions = {
            "fromright": f"movewindowpixel {off_x} 0",
            "fromleft": f"movewindowpixel {-off_x} 0",
            "frombottom": f"movewindowpixel 0 {off_y}",
            "fromtop": f"movewindowpixel 0 {-off_y}",
        }
        await self.hyprctl(
            [f"{animation_actions[animation_type]},address:{addr}" for addr in addresses if animation_type in animation_actions]
        )

    async def run_show(self, uid: str) -> None:
        """<name> shows scratchpad "name" (accepts "*")."""
        if uid == "*":
            await asyncio.gather(*(self.run_show(s.uid) for s in self.scratches.values() if not s.visible))
            return
        scratch = self.scratches.get(uid)

        if not scratch:
            self.log.warning("%s doesn't exist, can't hide.", uid)
            await notify_error(f"Scratchpad '{uid}' not found, check your configuration or the show parameter")
            return

        self.cancel_task(uid)

        self.log.info("Showing %s", uid)
        was_alive = await scratch.is_alive()
        if not await self.ensure_alive(uid):
            self.log.error("Failed to show %s, aborting.", uid)
            return

        excluded_ids = scratch.conf.get("excludes", [])
        restore_excluded = scratch.conf.get_bool("restore_excluded", False)
        if excluded_ids == "*":
            excluded_ids = [excluded.uid for excluded in self.scratches.values() if excluded.uid != scratch.uid]
        elif excluded_ids is None:
            excluded_ids = []

        for e_uid in cast("list[str]", excluded_ids):
            excluded = self.scratches.get(e_uid)
            assert excluded
            if excluded.visible:
                await self.run_hide(e_uid, flavor=HideFlavors.TRIGGERED_BY_AUTOHIDE | HideFlavors.IGNORE_TILED)
                if restore_excluded:
                    scratch.excluded_scratches.append(e_uid)

        await scratch.initialize(self)

        scratch.visible = True
        scratch.meta.space_identifier = get_active_space_identifier(self.state)
        monitor = await self.get_monitor_props(name=scratch.forced_monitor)

        assert monitor
        assert scratch.full_address, "No address !"

        await self._show_transition(scratch, monitor, was_alive)
        scratch.monitor = monitor["name"]

    async def _handle_multiwindow(self, scratch: Scratch, clients: list[ClientInfo]) -> bool:
        """Collect every matching client for the scratchpad and add them to extra_addr if needed."""
        if not scratch.conf.get_bool("multi", True):
            return False
        try:
            match_by, match_value = scratch.get_match_props()
        except KeyError:
            return False
        match_fn = get_match_fn(match_by, match_value)
        hit = False
        for client in clients:
            if client["address"] == scratch.full_address:
                continue
            if match_fn(client[match_by], match_value):  # type: ignore
                address = client["address"]
                if address not in scratch.extra_addr:
                    scratch.extra_addr.add(address)
                    if scratch.conf.get("pinned", True):
                        await self.hyprctl(f"pin address:{address}")
                    hit = True
        return hit

    async def _show_transition(self, scratch: Scratch, monitor: MonitorInfo, was_alive: bool) -> None:
        """Performs the transition to visible state."""
        forbid_special = not scratch.conf.get_bool("allow_special_workspace", True)
        wrkspc = (
            monitor["activeWorkspace"]["name"]
            if forbid_special
            or not monitor["specialWorkspace"]["name"]
            or monitor["specialWorkspace"]["name"].startswith("special:scratch")
            else monitor["specialWorkspace"]["name"]
        )
        if self.previously_focused_window:
            self.focused_window_tracking[scratch.uid] = FocusTracker(self.previously_focused_window, wrkspc)

        scratch.meta.last_shown = time.time()
        # Start the transition
        preserve_aspect = scratch.conf.get_bool("preserve_aspect")
        should_set_aspect = (
            not (preserve_aspect and was_alive) or scratch.monitor != self.state.active_monitor
        )  # Not aspect preserving or it's newly spawned
        if should_set_aspect:
            await self._fix_size(scratch, monitor)

        clients = await self.hyprctl_json("clients")
        await self._handle_multiwindow(scratch, clients)
        # move
        move_commands = [
            f"moveworkspacetomonitor {mk_scratch_name(scratch.uid)} {monitor['name']}",
            f"movetoworkspacesilent {wrkspc},address:{scratch.full_address}",
            f"alterzorder top,address:{scratch.full_address}",
        ]
        for addr in scratch.extra_addr:
            move_commands.extend(
                [
                    f"movetoworkspacesilent {wrkspc},address:{addr}",
                    f"alterzorder top,address:{addr}",
                ]
            )

        await self.hyprctl(move_commands)
        await self._update_infos(scratch, clients)

        position_fixed = False
        if should_set_aspect:
            position_fixed = await self._fix_position(scratch, monitor)

        if not position_fixed:
            relative_animation = preserve_aspect and was_alive and not should_set_aspect
            await self._animate_show(scratch, monitor, relative_animation)
        await self.hyprctl(f"focuswindow address:{scratch.full_address}")

        if not scratch.client_info["pinned"]:
            await self._pin_scratch(scratch)

        scratch.meta.last_shown = time.time()
        scratch.meta.monitor_info = monitor

    async def _pin_scratch(self, scratch: Scratch) -> None:
        """Pin the scratchpad."""
        if not scratch.conf.get("pinned", True):
            return
        await self.hyprctl(f"pin address:{scratch.full_address}")
        for addr in scratch.extra_addr:
            await self.hyprctl(f"pin address:{addr}")

    async def _update_infos(self, scratch: Scratch, clients: list[ClientInfo]) -> None:
        """Update the client info."""
        try:
            # Update position, size & workspace information (workspace properties have been created)
            await scratch.update_client_info(clients=clients)
        except KeyError:
            for alt_addr in scratch.extra_addr:
                # Get the client info for the extra addresses
                try:
                    client_info = await self.get_client_props(addr="0x" + alt_addr, clients=clients)
                    if not client_info:
                        continue
                    await scratch.update_client_info(clients=clients, client_info=client_info)
                except KeyError:
                    pass
                else:
                    break
            else:
                self.log.exception("Lost the client info for %s", scratch.uid)

    async def _animate_show(self, scratch: Scratch, monitor: MonitorInfo, relative_animation: bool) -> None:
        """Animate the show transition."""
        animation_type = get_animation_type(scratch)
        multiwin_enabled = scratch.conf.get_bool("multi", True)
        if animation_type:
            animation_commands = []

            if "size" not in scratch.client_info:
                await self.update_scratch_info(scratch)  # type: ignore

            if relative_animation:
                main_win_position = apply_offset((monitor["x"], monitor["y"]), scratch.meta.extra_positions[scratch.address])
            else:
                main_win_position = Placement.get(
                    animation_type,
                    monitor,
                    scratch.client_info,
                    scratch.conf.get_int("margin", DEFAULT_MARGIN),
                )
            animation_commands.append(list(main_win_position) + [scratch.full_address])

            if multiwin_enabled:
                for address in scratch.extra_addr:
                    off = scratch.meta.extra_positions.get(address)
                    if off:
                        pos = apply_offset(main_win_position, off)
                        animation_commands.append(list(pos) + [address])

            await self.hyprctl([f"movewindowpixel exact {a[0]} {a[1]},address:{a[2]}" for a in animation_commands])

    async def _fix_size(self, scratch: Scratch, monitor: MonitorInfo) -> None:
        """Apply the size from config."""
        size = scratch.conf.get("size")
        if size:
            width, height = convert_coords(cast("str", size), monitor)
            max_size = scratch.conf.get("max_size")
            if max_size:
                max_width, max_height = convert_coords(cast("str", max_size), monitor)
                width = min(max_width, width)
                height = min(max_height, height)
            await self.hyprctl(f"resizewindowpixel exact {width} {height},address:{scratch.full_address}")

    async def _fix_position(self, scratch: Scratch, monitor: MonitorInfo) -> bool:
        """Apply the `position` config parameter."""
        position = scratch.conf.get("position")
        if position:
            x_pos, y_pos = convert_coords(cast("str", position), monitor)
            x_pos_abs, y_pos_abs = x_pos + monitor["x"], y_pos + monitor["y"]
            await self.hyprctl(f"movewindowpixel exact {x_pos_abs} {y_pos_abs},address:{scratch.full_address}")
            return True
        return False

    async def run_hide(self, uid: str, flavor: HideFlavors = HideFlavors.NONE) -> None:  # noqa: C901
        """<name> hides scratchpad "name" (accepts "*")."""
        if uid == "*":
            await asyncio.gather(*(self.run_hide(s.uid) for s in self.scratches.values() if s.visible))
            return

        scratch = self.scratches.get(uid)

        if not scratch:
            await notify_error(f"Scratchpad '{uid}' not found, check your configuration or the hide parameter")
            self.log.warning("%s is not configured", uid)
            return

        if not await scratch.is_alive():
            return

        if flavor & HideFlavors.IGNORE_TILED and not scratch.client_info["floating"]:
            return

        active_window = self.state.active_window
        active_workspace = self.state.active_workspace

        if not scratch.visible and not flavor & HideFlavors.FORCED and not flavor & HideFlavors.TRIGGERED_BY_AUTOHIDE:
            await notify_error(f"Scratchpad '{uid}' is not visible, will not hide.")
            self.log.warning("%s is already hidden", uid)
            return

        await self._hide_scratch(scratch, active_window, active_workspace)

    async def _hide_scratch(self, scratch: Scratch, active_window: str, active_workspace: str) -> None:
        """Perform the actual hide operation."""
        clients = await self.hyprctl_json("clients")
        await scratch.update_client_info(clients=clients)
        ref_position = scratch.client_info["at"]
        monitor_info = scratch.meta.monitor_info
        scratch.meta.extra_positions[scratch.address] = compute_offset(ref_position, (monitor_info["x"], monitor_info["y"]))
        # collects window which have been created by the app
        if scratch.conf.get_bool("multi", True):
            await self._handle_multiwindow(scratch, clients)
            positions = {}
            for sub_client in clients:
                if sub_client["address"] in scratch.extra_addr:
                    positions[sub_client["address"]] = compute_offset(sub_client["at"], ref_position)
            scratch.meta.extra_positions.update(positions)
        scratch.visible = False
        scratch.meta.should_hide = False
        self.log.info("Hiding %s", scratch.uid)
        await self._pin_scratch(scratch)
        await self._hide_transition(scratch, monitor_info)

        if not scratch.conf.get_bool("close_on_hide", False):
            await self.hyprctl(f"movetoworkspacesilent {mk_scratch_name(scratch.uid)},address:{scratch.full_address}")

            for addr in scratch.extra_addr:
                await self.hyprctl(f"movetoworkspacesilent {mk_scratch_name(scratch.uid)},address:{addr}")
                await asyncio.sleep(0.01)
        else:
            await self.hyprctl(f"closewindow address:{scratch.full_address}")

            for addr in scratch.extra_addr:
                await self.hyprctl(f"closewindow address:{addr}")
                await asyncio.sleep(0.01)

        for e_uid in scratch.excluded_scratches:
            await self.run_show(e_uid)
        scratch.excluded_scratches.clear()
        await self._handle_focus_tracking(scratch, active_window, active_workspace, clients)

    async def _handle_focus_tracking(self, scratch: Scratch, active_window: str, active_workspace: str, clients: ClientInfo | dict) -> None:
        """Handle focus tracking."""
        if not scratch.conf.get_bool("smart_focus", True):
            return
        for track in self.focused_window_tracking.values():
            if scratch.have_address(track.prev_focused_window):
                track.clear()
        tracker = self.focused_window_tracking.get(scratch.uid)
        if tracker and not tracker.prev_focused_window_wrkspc.startswith("special:"):
            same_workspace = tracker.prev_focused_window_wrkspc == active_workspace
            t_pfw = tracker.prev_focused_window
            client = next(filter(lambda d: d.get("address") == t_pfw, cast("list[dict]", clients)), None)
            if (
                client
                and scratch.have_address(active_window)
                and same_workspace
                and not scratch.have_address(tracker.prev_focused_window)
                and not client["workspace"]["name"].startswith("special")
            ):
                self.log.debug("Previous scratch: %s", self.scratches.get(addr=tracker.prev_focused_window))
                await self.hyprctl(f"focuswindow address:{tracker.prev_focused_window}")

    # }}}


# }}}
