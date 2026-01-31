"""Scratchpad event handlers mixin."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, cast

from ...common import MINIMUM_ADDR_LEN
from .common import HideFlavors
from .helpers import get_match_fn

if TYPE_CHECKING:
    import logging

    from ...adapters.proxy import BackendProxy
    from ...aioops import TaskManager
    from ...models import ClientInfo
    from . import Extension
    from .lookup import ScratchDB
    from .objects import Scratch

__all__ = ["EventsMixin"]

AFTER_SHOW_INHIBITION = 0.3  # 300ms of ignorance after a show


class EventsMixin:
    """Mixin for scratchpad event handling.

    Handles Hyprland events related to windows and workspaces.
    """

    # Type hints for attributes provided by the composed class
    log: logging.Logger
    backend: BackendProxy
    scratches: ScratchDB
    _tasks: TaskManager
    workspace: str
    previously_focused_window: str
    last_focused: Scratch | None

    # Methods provided by the composed class
    def cancel_task(self, uid: str) -> bool:
        """Cancel a running task for a scratchpad."""
        _ = uid
        return False  # stub, overridden by composed class

    async def run_hide(self, uid: str, flavor: HideFlavors = HideFlavors.NONE) -> None:
        """Hide a scratchpad."""
        _ = uid, flavor  # stub, overridden by composed class

    async def update_scratch_info(self, orig_scratch: Scratch | None = None) -> None:
        """Update scratchpad information."""
        _ = orig_scratch  # stub, overridden by composed class

    async def _handle_multiwindow(self, scratch: Scratch, clients: list[ClientInfo]) -> bool:
        """Handle multi-window scratchpads."""
        _ = scratch, clients
        return False  # stub, overridden by composed class

    async def event_changefloatingmode(self, args: str) -> None:
        """Update the floating mode of scratchpads.

        Args:
            args: The arguments passed to the event
        """
        addr, _onoff = args.split(",")
        onoff = int(_onoff)
        for scratch in self.scratches.values():
            if scratch.address == addr and scratch.client_info is not None:
                scratch.client_info["floating"] = bool(onoff)

    async def event_workspace(self, name: str) -> None:
        """Workspace hook.

        Args:
            name: The workspace name
        """
        for scratch in self.scratches.values():
            scratch.event_workspace(name)

        self.workspace = name

    async def event_closewindow(self, addr: str) -> None:
        """Close window hook.

        Args:
            addr: The window address
        """
        # Removes this address from the extra_addr
        addr = "0x" + addr
        for scratch in self.scratches.values():
            if addr in scratch.extra_addr:
                scratch.extra_addr.remove(addr)
            if addr in scratch.meta.extra_positions:
                del scratch.meta.extra_positions[addr]

    async def event_monitorremoved(self, monitor_name: str) -> None:
        """Hides scratchpads on the removed screen.

        Args:
            monitor_name: The monitor name
        """
        for scratch in self.scratches.values():
            if scratch.monitor == monitor_name:
                try:
                    await self.run_hide(scratch.uid, flavor=HideFlavors.TRIGGERED_BY_AUTOHIDE)
                except (RuntimeError, OSError, ConnectionError) as e:
                    self.log.exception("Failed to hide %s", scratch.uid)
                    await self.backend.notify_info(f"Failed to hide {scratch.uid}: {e}")

    async def event_activewindowv2(self, addr: str) -> None:
        """Active windows hook.

        Args:
            addr: The window address
        """
        full_address = "" if not addr or len(addr) < MINIMUM_ADDR_LEN else "0x" + addr
        for uid, scratch in self.scratches.items():
            if scratch.client_info is None:
                continue
            if scratch.have_address(full_address):
                if scratch.full_address == full_address:
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
        """Hysteresis handling.

        Args:
            scratch: The scratchpad object
        """
        hysteresis = scratch.conf.get_float("hysteresis")
        if hysteresis:
            self.cancel_task(scratch.uid)

            async def _task(scratch: Scratch, delay: float) -> None:
                await asyncio.sleep(delay)
                self.log.debug("hide %s because another client is active", scratch.uid)
                await self.run_hide(scratch.uid, flavor=HideFlavors.TRIGGERED_BY_AUTOHIDE)

            self._tasks.create(_task(scratch, hysteresis), key=scratch.uid)
        else:
            self.log.debug("hide %s because another client is active", scratch.uid)
            await self.run_hide(scratch.uid, flavor=HideFlavors.TRIGGERED_BY_AUTOHIDE)

    async def _alternative_lookup(self) -> bool:
        """If not matching by pid, use specific matching and return True."""
        class_lookup_hack = [s for s in self.scratches.get_by_state("respawned") if s.conf.get("match_by") != "pid"]
        if not class_lookup_hack:
            return False
        self.log.debug("Lookup hack triggered")
        clients = cast("list[ClientInfo]", await self.backend.execute_json("clients"))
        for pending_scratch in class_lookup_hack:
            match_by, match_value = pending_scratch.get_match_props()
            match_fn = get_match_fn(match_by, match_value)
            for client in clients:
                if match_fn(client[match_by], match_value):  # type: ignore[literal-required]
                    self.scratches.register(pending_scratch, addr=client["address"][2:])
                    self.log.debug("client class found: %s", client)
                    await pending_scratch.update_client_info(client)
        return True

    async def event_openwindow(self, params: str) -> None:
        """Open windows hook.

        Args:
            params: The arguments passed to the event
        """
        addr, _wrkspc, _kls, _title = params.split(",", 3)
        item = self.scratches.get(addr=addr)
        respawned = list(self.scratches.get_by_state("respawned"))

        if item:
            # Ensure initialized (no-op if already initialized)
            await item.initialize(cast("Extension", self))
        elif respawned:
            # NOTE: for windows which aren't related to the process (see #8)
            if not await self._alternative_lookup():
                self.log.info("Updating Scratch info")
                await self.update_scratch_info()
            if item and item.meta.should_hide:
                await self.run_hide(item.uid, flavor=HideFlavors.FORCED)
        else:
            clients = await self.backend.execute_json("clients")
            for item in self.scratches.values():
                if await self._handle_multiwindow(item, clients):
                    return
