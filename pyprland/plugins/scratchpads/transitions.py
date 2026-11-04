"""Scratchpad transitions mixin."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from ...adapters.units import convert_coords, convert_monitor_dimension
from ...common import is_rotated
from .animations import AnimationTarget, Placement
from .common import ONE_FRAME, SIZE_RETRY_INTERVAL, SIZE_SETTLE_ATTEMPTS, FocusTracker
from .helpers import apply_offset

if TYPE_CHECKING:
    import logging

    from ...adapters.proxy import BackendProxy
    from ...common import SharedState
    from ...models import ClientInfo, MonitorInfo
    from .objects import Scratch

__all__ = ["TransitionsMixin"]


class TransitionsMixin:
    """Mixin for scratchpad show/hide transitions.

    Handles animations and positioning during visibility changes.
    """

    # Type hints for attributes provided by the composed class
    log: logging.Logger
    backend: BackendProxy
    state: SharedState
    previously_focused_window: str
    focused_window_tracking: dict[str, FocusTracker]

    # Methods provided by the composed class
    async def _handle_multiwindow(self, scratch: Scratch, clients: list[ClientInfo]) -> bool:
        """Handle multi-window scratchpads."""
        _ = scratch, clients
        return False  # stub, overridden by composed class

    async def update_scratch_info(self, orig_scratch: Scratch | None = None) -> None:
        """Update scratchpad information."""
        _ = orig_scratch  # stub, overridden by composed class

    async def get_offsets(self, scratch: Scratch, monitor: MonitorInfo | None = None) -> tuple[int, int]:
        """Return offset from config or use margin as a ref.

        Args:
            scratch: The scratchpad object
            monitor: The monitor info
        """
        if not scratch.client_ready:
            return (0, 0)
        assert scratch.client_info
        offset = scratch.conf.get("offset")
        if monitor is None:
            monitor = await self.backend.get_monitor_props(name=scratch.forced_monitor)
        rotated = is_rotated(monitor)
        aspect = reversed(scratch.client_info["size"]) if rotated else scratch.client_info["size"]

        margin = scratch.conf.get_int("margin")

        if offset:
            offset_str = str(offset)
            aspect_tuple = tuple(aspect)
            return (
                convert_monitor_dimension(offset_str, aspect_tuple[0], monitor, logical_ref=True) + margin,
                convert_monitor_dimension(offset_str, aspect_tuple[1], monitor, logical_ref=True) + margin,
            )

        mon_size = (monitor["height"], monitor["width"]) if rotated else (monitor["width"], monitor["height"])

        return (
            convert_monitor_dimension("100%", mon_size[0], monitor) + margin,
            convert_monitor_dimension("100%", mon_size[1], monitor) + margin,
        )

    async def _hide_transition(self, scratch: Scratch, monitor: MonitorInfo) -> bool:
        """Animate hiding a scratchpad.

        Args:
            scratch: The scratchpad object
            monitor: The monitor info
        """
        animation_type: str = scratch.animation_type

        if not animation_type or not self.backend.supports_offscreen_placement:
            # Niri clamps floating windows on-screen, so the slide-out would
            # just jitter the window before it is parked anyway.
            return False

        await self._slide_animation(animation_type, scratch, await self.get_offsets(scratch, monitor))
        delay: float = scratch.conf.get_float("hide_delay")
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
        """Slides the window `offset` pixels respecting `animation_type`.

        Args:
            animation_type: The animation type
            scratch: The scratchpad object
            offset: The offset to slide
            target: The target of the animation
        """
        addresses: list[str] = []
        if target != AnimationTarget.MAIN:
            addresses.extend(scratch.extra_addr)
        if target != AnimationTarget.EXTRA:
            addresses.append(scratch.full_address)
        off_x, off_y = offset

        if scratch.client_info:
            x, y = scratch.client_info.get("at", (0, 0))
        else:
            x, y = 0, 0

        animation_offsets = {
            "fromright": (off_x, 0),
            "fromleft": (-off_x, 0),
            "frombottom": (0, off_y),
            "fromtop": (0, -off_y),
            "fromtopright": (off_x, -off_y),
            "fromtopleft": (-off_x, -off_y),
            "frombottomright": (off_x, off_y),
            "frombottomleft": (-off_x, off_y),
        }
        if animation_type not in animation_offsets:
            return
        dx, dy = animation_offsets[animation_type]
        await self.backend.move_windows([(addr, x + dx, y + dy) for addr in addresses])

    async def _show_transition(self, scratch: Scratch, monitor: MonitorInfo, was_alive: bool) -> None:
        """Performs the transition to visible state.

        Args:
            scratch: The scratchpad object
            monitor: The monitor info
            was_alive: Whether the scratchpad was already alive
        """
        forbid_special = not scratch.conf.get_bool("allow_special_workspaces")
        wrkspc = (
            monitor["activeWorkspace"]["name"]
            if forbid_special
            or not monitor["specialWorkspace"]["name"]
            or self.backend.is_scratch_workspace(monitor["specialWorkspace"]["name"])
            else monitor["specialWorkspace"]["name"]
        )
        if self.previously_focused_window:
            self.focused_window_tracking[scratch.uid] = FocusTracker(self.previously_focused_window, wrkspc)

        scratch.meta.last_shown = time.time()
        # Start the transition
        preserve_aspect = scratch.conf.get_bool("preserve_aspect")
        should_set_aspect = not (preserve_aspect and was_alive)
        # Not aspect preserving or it's newly spawned
        animation_type = scratch.animation_type

        requested_size: tuple[int, int] | None = None
        if should_set_aspect or scratch.address not in scratch.meta.saved_size:
            # `preserve_aspect` needs a size recorded on a previous hide;
            # without one, fall back to the configured size — otherwise a
            # freshly spawned window keeps whatever size the compositor gave it.
            requested_size = await self._fix_size(scratch, monitor)
        else:
            # Restore the saved pixel size (preserve_aspect enabled)
            requested_size = scratch.meta.saved_size[scratch.address]
            await self.backend.resize_window(scratch.full_address, *requested_size)

        clients = await self.backend.execute_json("clients")
        await self._handle_multiwindow(scratch, clients)

        # FIX: initial position
        # Suppress the compositor's own animation during the offscreen
        # pre-positioning move, then restore it so the slide-in plays normally.
        # Backends without per-window animation control simply show the jump.
        if animation_type and scratch.client_ready and self.backend.supports_offscreen_placement:
            assert scratch.client_info is not None
            off_x, off_y = Placement.get_offscreen(
                animation_type,
                monitor,
                scratch.client_info,
                scratch.conf.get_int("margin"),
            )
            await self.backend.set_window_animations([scratch.full_address], enabled=False)
            await self.backend.move_windows([(scratch.full_address, off_x, off_y)])
            await asyncio.sleep(ONE_FRAME)  # NOTE: let some time to process
            await self.backend.set_window_animations([scratch.full_address], enabled=True)

        # move
        # Only move workspace to monitor if scratchpad was already alive
        # (newly spawned windows are already on current monitor via windowrules)
        if was_alive:
            await self.backend.move_workspace_to_monitor(self.backend.scratch_workspace(scratch.uid), monitor["name"])

        addresses = [scratch.full_address, *scratch.extra_addr]
        await self.backend.move_windows_to_workspace(addresses, wrkspc, silent=True)
        await self.backend.raise_windows(addresses)

        await self._update_infos(scratch, clients)

        # Always apply an explicit `position`: it is a user intent that should
        # always be honored, regardless of should_set_aspect.
        position_fixed = await self._fix_position(scratch, monitor)

        monitor_changed = scratch.monitor != self.state.active_monitor
        relative_animation = preserve_aspect and was_alive and not monitor_changed
        if not position_fixed:
            await self._animate_show(scratch, monitor, relative_animation)
        await self.backend.focus_window(scratch.full_address)

        # Re-apply position after a settle delay, since some apps resize
        # themselves after being shown, which shifts the window.
        if not self.backend.supports_offscreen_placement:
            await self._settle_geometry(scratch, monitor, requested_size, relative_animation, position_fixed)
        elif position_fixed:
            await asyncio.sleep(ONE_FRAME)
            await self._fix_position(scratch, monitor)

        if scratch.client_info is None or not scratch.client_info["pinned"]:
            await self._pin_scratch(scratch)

        scratch.meta.last_shown = time.time()
        scratch.meta.monitor_info = monitor

    async def _pin_scratch(self, scratch: Scratch) -> None:
        """Pin the scratchpad.

        Args:
            scratch: The scratchpad object
        """
        if not scratch.conf.get("pinned"):
            return
        await self.backend.pin_window(scratch.full_address)
        for addr in scratch.extra_addr:
            await self.backend.pin_window(addr)

    async def _update_infos(self, scratch: Scratch, clients: list[ClientInfo]) -> None:
        """Update the client info.

        Args:
            scratch: The scratchpad object
            clients: The list of clients
        """
        try:
            # Update position, size & workspace information (workspace properties have been created)
            await scratch.update_client_info(clients=clients)
        except KeyError:
            for alt_addr in scratch.extra_addr:
                # Get the client info for the extra addresses
                try:
                    client_info = await self.backend.get_client_props(addr=self.backend.full_address(alt_addr), clients=clients)
                    if not client_info:
                        continue
                    await scratch.update_client_info(clients=clients, client_info=client_info)
                except KeyError:
                    self.log.debug("Client info not found for address %s", alt_addr)
                else:
                    break
            else:
                self.log.exception("Lost the client info for %s", scratch.uid)

    async def _animate_show(self, scratch: Scratch, monitor: MonitorInfo, relative_animation: bool) -> None:
        """Animate the show transition.

        Args:
            scratch: The scratchpad object
            monitor: The monitor info
            relative_animation: Whether to use relative animation
        """
        animation_type = scratch.animation_type
        multiwin_enabled = scratch.conf.get_bool("multi")
        if animation_type:
            animation_commands = []

            if scratch.client_info is None or "size" not in scratch.client_info:
                await self.update_scratch_info(scratch)

            if scratch.client_info is None:
                self.log.error("Cannot animate show: client_info is None for %s", scratch.uid)
                return

            if relative_animation and scratch.address in scratch.meta.extra_positions:
                main_win_position = apply_offset((monitor["x"], monitor["y"]), scratch.meta.extra_positions[scratch.address])
            else:
                main_win_position = Placement.get(
                    animation_type,
                    monitor,
                    scratch.client_info,
                    scratch.conf.get_int("margin"),
                )
            animation_commands.append([*main_win_position, scratch.full_address])

            if multiwin_enabled:
                for address in scratch.extra_addr:
                    off = scratch.meta.extra_positions.get(address)
                    if off:
                        pos = apply_offset(main_win_position, off)
                        animation_commands.append([*pos, address])

            await self.backend.move_windows([(a[2], a[0], a[1]) for a in animation_commands])

    async def _fix_size(self, scratch: Scratch, monitor: MonitorInfo) -> tuple[int, int] | None:
        """Apply the size from config.

        Args:
            scratch: The scratchpad object
            monitor: The monitor info

        Returns:
            The requested (width, height), or None when no size is configured.
        """
        size = scratch.conf.get_str("size")
        if size:
            width, height = convert_coords(size, monitor)
            max_size = scratch.conf.get_str("max_size")
            if max_size:
                max_width, max_height = convert_coords(max_size, monitor)
                width = min(max_width, width)
                height = min(max_height, height)
            await self.backend.resize_window(scratch.full_address, width, height)
            self.log.debug("%s size %s -> %dx%d", scratch.uid, size, width, height)
            return (width, height)
        return None

    async def _await_size(self, scratch: Scratch, size: tuple[int, int]) -> None:
        """Make sure the compositor really applied the configured size.

        A resize is asynchronous, and on backends that place a window after
        mapping the request can be dropped — moving the window to its workspace
        or into the floating layer resets it to the default size. So poll until
        it lands, re-issuing the resize periodically.

        Args:
            scratch: The scratchpad object
            size: The requested (width, height)
        """
        for attempt in range(SIZE_SETTLE_ATTEMPTS):
            await asyncio.sleep(ONE_FRAME)
            await self.update_scratch_info(scratch)
            if scratch.client_info and tuple(scratch.client_info.get("size", ())) == size:
                return
            if attempt % SIZE_RETRY_INTERVAL == SIZE_RETRY_INTERVAL - 1:
                await self.backend.resize_window(scratch.full_address, *size)
        self.log.debug("%s did not reach the requested size %s", scratch.uid, size)

    async def _settle_geometry(
        self,
        scratch: Scratch,
        monitor: MonitorInfo,
        requested_size: tuple[int, int] | None,
        relative_animation: bool,
        position_fixed: bool,
    ) -> None:
        """Re-apply a window's geometry once its size has actually landed.

        Placement used the size reported before `_fix_size` took effect,
        leaving the window off by half the difference. Hyprland hides that
        behind the off-screen pre-positioning; backends without it show the
        stale geometry, so settle the size first, then place the window again.

        Args:
            scratch: The scratchpad object
            monitor: The monitor info
            requested_size: The size `_fix_size` asked for, if any
            relative_animation: Whether to use relative animation
            position_fixed: Whether an explicit `position` was configured
        """
        if requested_size:
            await self._await_size(scratch, requested_size)
        else:
            await asyncio.sleep(ONE_FRAME)
        if position_fixed:
            await self._fix_position(scratch, monitor)
        else:
            await self._animate_show(scratch, monitor, relative_animation)

    async def _fix_position(self, scratch: Scratch, monitor: MonitorInfo) -> bool:
        """Apply the `position` config parameter.

        Args:
            scratch: The scratchpad object
            monitor: The monitor info
        """
        position = scratch.conf.get_str("position")
        if position:
            x_pos, y_pos = convert_coords(position, monitor)
            x_pos_abs, y_pos_abs = x_pos + monitor["x"], y_pos + monitor["y"]
            await self.backend.move_window(scratch.full_address, x_pos_abs, y_pos_abs)
            return True
        return False
