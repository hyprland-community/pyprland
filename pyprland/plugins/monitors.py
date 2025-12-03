"""The monitors plugin."""

import asyncio
from collections import defaultdict
from copy import deepcopy
from typing import Any, cast

from ..common import CastBoolMixin, is_rotated, state
from ..types import MonitorInfo
from .interface import Plugin

MONITOR_PROPS = {"scale", "transform", "rate", "resolution"}


def trim_offset(monitors: list[MonitorInfo]) -> None:
    """Make the monitor set layout start at 0,0."""
    off_x = None
    off_y = None
    for mon in monitors:
        if off_x is None:
            off_x = mon["x"]

        if off_y is None:
            off_y = mon["y"]

        off_x = min(mon["x"], off_x)
        off_y = min(mon["y"], off_y)

    assert off_x is not None
    assert off_y is not None

    for mon in monitors:
        mon["x"] -= off_x
        mon["y"] -= off_y


def clean_pos(position: str) -> str:
    """Harmonize position format."""
    return position.lower().replace("_", "").replace("-", "")


def scale_and_rotate_mon(monitor: MonitorInfo) -> tuple[int, int]:
    """Scale and rotate the monitor dimensions."""
    width = int(monitor["width"] / monitor["scale"])
    height = int(monitor["height"] / monitor["scale"])
    if is_rotated(monitor):
        width, height = height, width
    return width, height


def get_xy(place: str, main_mon: MonitorInfo, other_mon: MonitorInfo) -> tuple[int, int]:
    """Get the XY position of a monitor according to another (after `place` is applied).

    Place syntax: "<top|left|bottom|right> [center|middle|end] of" (without spaces)
    """
    align_x = False  # if alignment is on X axis, else on Y axis
    scaled_m_w, scaled_m_h = scale_and_rotate_mon(main_mon)
    scaled_om_w, scaled_om_h = scale_and_rotate_mon(other_mon)

    if place[0] in ("t", "b"):  # top or bottom
        align_x = True
        x = other_mon["x"]
        y = other_mon["y"] - scaled_m_h if place[0] == "t" else other_mon["y"] + scaled_om_h
    else:  # left or right
        y = other_mon["y"]
        x = other_mon["x"] - scaled_m_w if place[0] == "l" else other_mon["x"] + scaled_om_w

    centered = "middle" in place or "center" in place

    if align_x:
        if centered:
            x += int((scaled_om_w - scaled_m_w) / 2)
        elif "end" in place:
            x += int(scaled_om_w - scaled_m_w)
    elif centered:
        y += int((scaled_om_h - scaled_m_h) / 2)
    elif "end" in place:
        y -= scaled_m_h - scaled_om_h

    return (x, y)


def build_graph(config: dict[str, dict[str, list[str]]]) -> dict[str, list[str]]:
    """Make a sorted graph based on the cleaned_config."""
    graph = defaultdict(list)
    for name1, positions in config.items():
        for pos, names in positions.items():
            if pos in MONITOR_PROPS:
                continue
            tldr_direction = pos.startswith(("left", "top"))
            for name2 in names:
                if tldr_direction:
                    graph[name1].append(name2)
                else:
                    graph[name2].append(name1)
    return graph


class Extension(CastBoolMixin, Plugin):  # pylint: disable=missing-class-docstring
    """Control monitors layout."""

    _mon_by_pat_cache: dict[str, MonitorInfo] = {}

    async def on_reload(self) -> None:
        """Reload the plugin."""
        self._clear_mon_by_pat_cache()
        monitors = await self.hyprctl_json("monitors")

        for mon in state.monitors:
            await self._hotplug_command(name=mon, monitors=monitors)

        if self.cast_bool(self.config.get("startup_relayout"), True):
            # run relayout after 1second without blocking

            async def _delayed_relayout() -> None:
                await self._run_relayout(monitors)
                await asyncio.sleep(1)
                await self._run_relayout()

            await asyncio.create_task(_delayed_relayout())

    def _build_monitor_command(self, monitor: MonitorInfo, config: dict[str, dict[str, Any]], every_monitor: dict[str, MonitorInfo]) -> str:
        """Build the monitor command."""
        name = monitor["name"]
        this_config = config.get(name, {})
        rate = this_config.get("rate", every_monitor[name]["refreshRate"])
        res = this_config.get("resolution", f"{every_monitor[name]['width']}x{every_monitor[name]['height']}")
        if isinstance(res, list):
            res = f"{res[0]}x{res[1]}"
        scale = this_config.get("scale", every_monitor[name]["scale"])
        position = f"{monitor['x']}x{monitor['y']}"
        transform = this_config.get("transform", every_monitor[name]["transform"])
        return f"monitor {name},{res}@{rate},{position},{scale},transform,{transform}"

    # Command

    async def run_relayout(self) -> bool:
        """Recompute & apply every monitors's layout."""
        return await self._run_relayout()

    async def _run_relayout(self, monitors: list[MonitorInfo] | str | None = None) -> bool:
        """Recompute & apply every monitors's layout."""
        if isinstance(monitors, str):
            self.log.error("relayout doesn't take any argument")
            await self.notify_error("relayout doesn't take any argument")
            return False

        iterations = 3
        for n in range(iterations):
            await asyncio.sleep(0.1)
            self._clear_mon_by_pat_cache()

            if monitors is None or n < iterations - 1:
                monitors = cast("list[MonitorInfo]", await self.hyprctl_json("monitors"))

            cleaned_config = self.resolve_names(monitors)
            if cleaned_config:
                self.log.debug("Using %s", cleaned_config)
            else:
                self.log.debug("No configuration item is applicable")
                return False
            graph = build_graph(cleaned_config)
            need_change = self._update_positions(monitors, graph, cleaned_config)
            every_monitor = {v["name"]: v for v in await self.hyprctl_json("monitors all")}
            if self.cast_bool(self.config.get("trim_offset"), True):
                trim_offset(monitors)

            for monitor in sorted(monitors, key=lambda x: x["x"] + x["y"]):
                cmd = self._build_monitor_command(monitor, cleaned_config, every_monitor)
                self.log.debug(cmd)
                await self.hyprctl(cmd, "keyword")
        return need_change

    # Event handlers

    async def event_configreloaded(self, _: str = "") -> None:
        """Relayout screens after settings has been lost."""
        if self.config.get("relayout_on_config_change", True):
            await asyncio.sleep(1.0)
            await self.run_relayout()

    async def event_monitoradded(self, name: str) -> None:
        """Triggers when a monitor is plugged."""
        await asyncio.sleep(self.config.get("new_monitor_delay", 1.0))
        monitors = await self.hyprctl_json("monitors")
        await self._hotplug_command(monitors, name)

        if not await self._run_relayout(monitors):
            default_command = self.config.get("unknown")
            if default_command:
                await asyncio.create_subprocess_shell(default_command)

    # Utils

    async def _hotplug_command(self, monitors: list[MonitorInfo], name: str) -> None:
        """Run the hotplug command for the monitor."""
        monitors_by_descr = {m["description"]: m for m in monitors}
        monitors_by_name = {m["name"]: m for m in monitors}
        for descr, command in self.config.get("hotplug_commands", {}).items():
            mon = self._get_mon_by_pat(descr, monitors_by_descr, monitors_by_name)
            if mon and mon["name"] == name:
                await asyncio.create_subprocess_shell(command)
                break
        single_command = self.config.get("hotplug_command")
        if single_command:
            await asyncio.create_subprocess_shell(single_command)

    def _clear_mon_by_pat_cache(self) -> None:
        """Clear the cache."""
        self._mon_by_pat_cache: dict[str, MonitorInfo] = {}

    def _get_mon_by_pat(self, pat: str, description_db: dict[str, MonitorInfo], name_db: dict[str, MonitorInfo]) -> MonitorInfo | None:
        """Return a (plugged) monitor object given its pattern or none if not found."""
        cached = self._mon_by_pat_cache.get(pat)
        if cached is None:
            cached = name_db.get(pat)
            if cached is None:
                for full_descr in description_db:
                    if pat in full_descr:
                        cached = description_db[full_descr]
                        break
            if cached:
                self._mon_by_pat_cache[pat] = cached
        return cached

    _flipped_positions = {
        "topof": "bottomof",
        "bottomof": "topof",
        "leftof": "rightof",
        "rightof": "leftof",
        "topmiddleof": "bottommiddleof",
        "bottommiddleof": "topmiddleof",
        "leftmiddleof": "rightmiddleof",
        "rightmiddleof": "leftmiddleof",
        "topcenterof": "bottomcenterof",
        "bottomcenterof": "topcenterof",
        "leftcenterof": "rightcenterof",
        "rightcenterof": "leftcenterof",
        "topendof": "bottomendof",
        "bottomendof": "topendof",
        "leftendof": "rightendof",
        "rightendof": "leftendof",
    }

    def _update_positions(self, monitors: list[MonitorInfo], graph: dict[str, list[str]], config: dict[str, dict[str, list[str]]]) -> bool:
        """Apply configuration to monitors_by_name using graph."""
        monitors_by_name = {m["name"]: m for m in monitors}
        requires_update = False
        for _ in range(len(monitors_by_name) ** 2):
            changed = False
            for name in reversed(graph):
                mon1 = monitors_by_name[name]
                for name2 in graph[name]:
                    mon2 = monitors_by_name[name2]
                    for pos, _ in self.get_matching_config(name, name2, config):
                        try:
                            x, y = get_xy(self._flipped_positions[pos.lower()], mon2, mon1)
                        except TypeError:
                            self.log.exception("Invalid position %s", pos)
                            continue
                        if x != mon2["x"]:
                            changed = True
                            requires_update = True
                            mon2["x"] = x
                        if y != mon2["y"]:
                            changed = True
                            requires_update = True
                            mon2["y"] = y
            if not changed:
                break
        return requires_update

    def get_matching_config(self, name1: str, name2: str, config: dict[str, dict[str, list[str]]]) -> list[tuple[str, str]]:
        """Return rules matching name1 or name2 (relative to name1), looking up config.

        Returns a list of tuples (position, name) where name is the other monitor's name.
        """
        results = []
        ref_set = {name1, name2}
        for name_a, positions in config.items():
            for pos, names in positions.items():
                if pos in MONITOR_PROPS:
                    continue
                lpos = clean_pos(pos)
                for name_b in names:
                    if {name_a, name_b} == ref_set:
                        if name_a == name1:
                            results.append((lpos, name_b))
                        else:
                            results.append((self._flipped_positions[lpos], name_a))
        return results

    def resolve_names(self, monitors: list[MonitorInfo]) -> dict[str, Any]:
        """Change partial descriptions used in config for monitor names.

        Args:
            monitors: list of plugged monitors
        Returns:
            dict: cleaned config
        """
        monitors_by_descr = {m["description"]: m for m in monitors}
        cleaned_config: dict[str, dict[str, Any]] = {}
        plugged_monitors = {m["name"]: m for m in monitors}
        for descr1, placement in deepcopy(self.config.get("placement", {})).items():
            mon = self._get_mon_by_pat(descr1, monitors_by_descr, plugged_monitors)
            if not mon:
                continue
            name = mon["name"]
            if name not in plugged_monitors:
                continue
            cleaned_config[name] = {}
            for position, descr_list in placement.items():
                if position in MONITOR_PROPS:
                    cleaned_config[name][position] = descr_list
                else:
                    if not isinstance(descr_list, list | str):
                        errmsg = f'Unexpected monitor setting: {position}: "{descr_list}"'
                        raise ValueError(errmsg)
                    resolved = []
                    for props in [descr_list] if isinstance(descr_list, str) else descr_list:
                        info = self._get_mon_by_pat(props, monitors_by_descr, plugged_monitors)
                        if info:
                            resolved.append(info["name"])
                    if resolved:
                        cleaned_config[name][clean_pos(position)] = [r for r in resolved if r in plugged_monitors]
        return cleaned_config
