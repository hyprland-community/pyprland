"""Scratchpad transitions mixin."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, cast

from ...adapters.units import convert_coords, convert_monitor_dimension
from ...common import is_rotated
from .animations import AnimationTarget, Placement
from .common import FocusTracker
from .helpers import apply_offset, mk_scratch_name

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
        offset = scratch.conf.get("offset")
        if monitor is None:
            monitor = await self.backend.get_monitor_props(name=scratch.forced_monitor)
        rotated = is_rotated(monitor)
        aspect = reversed(scratch.client_info["size"]) if rotated else scratch.client_info["size"]

        if offset:
            return cast("tuple[int, int]", (convert_monitor_dimension(cast("str", offset), ref, monitor) for ref in aspect))

        mon_size = [monitor["height"], monitor["width"]] if rotated else [monitor["width"], monitor["height"]]

        offsets = [convert_monitor_dimension("100%", dim, monitor) for dim in mon_size]
        return cast("tuple[int, int]", offsets)

    async def _hide_transition(self, scratch: Scratch, monitor: MonitorInfo) -> bool:
        """Animate hiding a scratchpad.

        Args:
            scratch: The scratchpad object
            monitor: The monitor info
        """
        animation_type: str = scratch.animation_type

        if not animation_type:
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

        animation_actions = {
            "fromright": f"movewindowpixel {off_x} 0",
            "fromleft": f"movewindowpixel {-off_x} 0",
            "frombottom": f"movewindowpixel 0 {off_y}",
            "fromtop": f"movewindowpixel 0 {-off_y}",
        }
        await self.backend.execute(
            [f"{animation_actions[animation_type]},address:{addr}" for addr in addresses if animation_type in animation_actions]
        )

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

        clients = await self.backend.execute_json("clients")
        await self._handle_multiwindow(scratch, clients)
        # move
        move_commands: list[str] = []

        # Only move workspace to monitor if scratchpad was already alive
        # (newly spawned windows are already on current monitor via windowrules)
        if was_alive:
            move_commands.append(f"moveworkspacetomonitor {mk_scratch_name(scratch.uid)} {monitor['name']}")

        move_commands.extend(
            [
                f"movetoworkspacesilent {wrkspc},address:{scratch.full_address}",
                f"alterzorder top,address:{scratch.full_address}",
            ]
        )
        for addr in scratch.extra_addr:
            move_commands.extend(
                [
                    f"movetoworkspacesilent {wrkspc},address:{addr}",
                    f"alterzorder top,address:{addr}",
                ]
            )

        await self.backend.execute(move_commands, weak=True)
        await self._update_infos(scratch, clients)

        position_fixed = False
        if should_set_aspect:
            position_fixed = await self._fix_position(scratch, monitor)

        if not position_fixed:
            relative_animation = preserve_aspect and was_alive and not should_set_aspect
            await self._animate_show(scratch, monitor, relative_animation)
        await self.backend.focus_window(scratch.full_address)

        if not scratch.client_info["pinned"]:
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
                    client_info = await self.backend.get_client_props(addr="0x" + alt_addr, clients=clients)
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

            if "size" not in scratch.client_info:
                await self.update_scratch_info(scratch)  # type: ignore

            if relative_animation:
                main_win_position = apply_offset((monitor["x"], monitor["y"]), scratch.meta.extra_positions[scratch.address])
            else:
                main_win_position = Placement.get(
                    animation_type,
                    monitor,
                    scratch.client_info,
                    scratch.conf.get_int("margin"),
                )
            animation_commands.append(list(main_win_position) + [scratch.full_address])

            if multiwin_enabled:
                for address in scratch.extra_addr:
                    off = scratch.meta.extra_positions.get(address)
                    if off:
                        pos = apply_offset(main_win_position, off)
                        animation_commands.append(list(pos) + [address])

            await self.backend.execute([f"movewindowpixel exact {a[0]} {a[1]},address:{a[2]}" for a in animation_commands])

    async def _fix_size(self, scratch: Scratch, monitor: MonitorInfo) -> None:
        """Apply the size from config.

        Args:
            scratch: The scratchpad object
            monitor: The monitor info
        """
        size = scratch.conf.get("size")
        if size:
            width, height = convert_coords(cast("str", size), monitor)
            max_size = scratch.conf.get("max_size")
            if max_size:
                max_width, max_height = convert_coords(cast("str", max_size), monitor)
                width = min(max_width, width)
                height = min(max_height, height)
            await self.backend.resize_window(scratch.full_address, width, height)

    async def _fix_position(self, scratch: Scratch, monitor: MonitorInfo) -> bool:
        """Apply the `position` config parameter.

        Args:
            scratch: The scratchpad object
            monitor: The monitor info
        """
        position = scratch.conf.get("position")
        if position:
            x_pos, y_pos = convert_coords(cast("str", position), monitor)
            x_pos_abs, y_pos_abs = x_pos + monitor["x"], y_pos + monitor["y"]
            await self.backend.move_window(scratch.full_address, x_pos_abs, y_pos_abs)
            return True
        return False
