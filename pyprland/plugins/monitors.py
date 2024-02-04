" The monitors plugin "
import asyncio
import subprocess
from collections import defaultdict
from copy import deepcopy
from typing import Any, cast

from .interface import Plugin


def trim_offset(monitors):
    "Makes the monitor set layout start at 0,0"
    off_x = None
    off_y = None
    for mon in monitors:
        if off_x is None:
            off_x = mon["x"]

        if off_y is None:
            off_y = mon["y"]

        off_x = min(mon["x"], off_x)
        off_y = min(mon["y"], off_y)

    for mon in monitors:
        mon["x"] -= off_x
        mon["y"] -= off_y


def clean_pos(position):
    "Harmonize position format"
    return position.lower().replace("_", "").replace("-", "")


def get_XY(place, main_mon, other_mon):
    """Get the XY position of a monitor according to another (after `place` is applied)
    Place syntax: "<top|left|bottom|right> [center|middle|end] of" (without spaces)
    """
    align_x = False
    scaled_m_w = int(main_mon["width"] / main_mon["scale"])
    scaled_m_h = int(main_mon["height"] / main_mon["scale"])
    scaled_om_w = int(other_mon["width"] / other_mon["scale"])
    scaled_om_h = int(other_mon["height"] / other_mon["scale"])
    if place.startswith("top"):
        x = other_mon["x"]
        y = other_mon["y"] - scaled_m_h
        align_x = True
    elif place.startswith("bottom"):
        x = other_mon["x"]
        y = other_mon["y"] + scaled_om_h
        align_x = True
    elif place.startswith("left"):
        x = other_mon["x"] - scaled_m_w
        y = other_mon["y"]
    elif place.startswith("right"):
        x = other_mon["x"] + scaled_om_w
        y = other_mon["y"]
    else:
        return None

    centered = "middle" in place or "center" in place

    if align_x:
        if centered:
            x += int((scaled_om_w - scaled_m_w) / 2)
        elif "end" in place:
            x += int(scaled_om_w - scaled_m_w)
    else:
        if centered:
            y += int((scaled_om_h - scaled_m_h) / 2)
        elif "end" in place:
            y += scaled_m_h - scaled_om_h
    return (x, y)


def apply_monitor_position(monitors, screenid: str, pos_x: int, pos_y: int) -> None:
    "Apply the configuration change"

    command = ["wlr-randr"]
    monitor = [mon for mon in monitors if mon["name"] == screenid][0]

    monitor["x"] = pos_x
    monitor["y"] = pos_y

    command.extend(["--output", screenid, "--pos", f"{pos_x},{pos_y}"])
    subprocess.call(command)


def build_graph(config):
    "make a sorted graph based on the cleaned_config"
    graph = defaultdict(list)
    for name1, positions in config.items():
        for pos, names in positions.items():
            tldr_direction = pos.startswith("left") or pos.startswith("top")
            for name2 in names:
                if tldr_direction:
                    graph[name1].append(name2)
                else:
                    graph[name2].append(name1)
    return graph


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    _mon_by_pat_cache: dict[str, dict] = {}

    async def load_config(self, config) -> None:
        await super().load_config(config)
        if self.config.get("startup_relayout", True):
            await self.run_relayout()

    # Command

    async def run_relayout(
        self,
    ):
        "Recompute & apply every monitors's layout"

        monitors = cast(list[dict], await self.hyprctlJSON("monitors"))

        cleaned_config = self.resolve_names(monitors)
        graph = build_graph(cleaned_config)
        self._update_positions(monitors, graph, cleaned_config)
        trim_offset(monitors)

        command = ["wlr-randr"]
        for monitor in sorted(monitors, key=lambda x: x["x"] + x["y"]):
            command.extend(
                ["--output", monitor["name"], "--pos", f'{monitor["x"]},{monitor["y"]}']
            )
        subprocess.call(command)

    # Event handlers

    async def event_monitoradded(self, monitor_name) -> None:
        "Triggers when a monitor is plugged"

        if self.config.get("full_relayout", False):
            await self.run_relayout()
        else:
            monitors = cast(list, await self.hyprctlJSON("monitors"))

            assert monitors

            for mon in monitors:
                if mon["name"].startswith(monitor_name):
                    mon_info = mon
                    break
            else:
                self.log.warning("Monitor %s not found", monitor_name)
                return

            default_command = self.config.get("unknown")
            if self._place_single_monitor(mon_info, monitors) and default_command:
                await asyncio.create_subprocess_shell(default_command)

    # Utils

    def _clear_mon_by_pat_cache(self):
        "clear the cache"
        self._mon_by_pat_cache = {}

    def _get_mon_by_pat(self, pat, database):
        """Returns a (plugged) monitor object given its pattern or none if not found"""
        cached = self._mon_by_pat_cache.get(pat)
        if cached:
            return cached
        for full_descr in database:
            if pat in full_descr:
                cached = database[full_descr]
                self._mon_by_pat_cache[pat] = cast(dict[str, dict], cached)
                break
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

    def _get_rules(self, mon_name, placement):
        "build a list of matching rules from the config"
        for pattern, config in placement.items():
            matched = pattern == mon_name
            for position, descr_list in config.items():
                if isinstance(descr_list, str):
                    descr_list = [descr_list]
                for descr in descr_list:
                    lp = clean_pos(position)
                    if matched or descr == mon_name:
                        yield (
                            lp if matched else self._flipped_positions[lp],
                            descr,
                            f"{pattern} {config}",
                        )

    def _place_single_monitor(
        self,
        mon_info: dict[str, int | float | str | list],
        monitors: list[dict[str, Any]],
    ):
        "place a given monitor according to config"

        mon_name: str = cast(str, mon_info["name"])
        monitors_by_name = {m["name"]: m for m in monitors}
        self._clear_mon_by_pat_cache()
        matched = False

        cleaned_config = self.resolve_names(monitors)
        for place, other_screen, rule in self._get_rules(
            mon_info["name"], cleaned_config
        ):
            other_mon = monitors_by_name.get(other_screen)

            if other_mon:
                matched = True
                pos = get_XY(place, mon_info, other_mon)
                if pos:
                    x, y = pos
                    self.log.info("Will place %s @ %s,%s (%s)", mon_name, x, y, rule)
                    apply_monitor_position(monitors, mon_name, x, y)
                else:
                    self.log.error("Unknown position type: %s (%s)", place, rule)

        return matched

    def _update_positions(self, monitors, graph, config):
        "Apply configuration to monitors_by_name using graph"
        monitors_by_name = {m["name"]: m for m in monitors}
        for _ in range(len(monitors_by_name) ** 2):
            changed = False
            for name in reversed(graph):
                mon1 = monitors_by_name[name]
                for name2 in graph[name]:
                    mon2 = monitors_by_name[name2]
                    for pos, _ in self.get_matching_config(name, name2, config):
                        x, y = get_XY(self._flipped_positions[pos], mon2, mon1)
                        if x != mon2["x"]:
                            changed = True
                            mon2["x"] = x
                        if y != mon2["y"]:
                            changed = True
                            mon2["y"] = y
            if not changed:
                break

    def get_matching_config(self, name1, name2, config):
        "Returns rules matching name1 or name2 (relative to name1), looking up config"
        results = []
        ref_set = set((name1, name2))
        for name_a, positions in config.items():
            for pos, names in positions.items():
                lpos = clean_pos(pos)
                for name_b in names:
                    if set((name_a, name_b)) == ref_set:
                        if name_a == name1:
                            results.append((lpos, name_b))
                        else:
                            results.append((self._flipped_positions[lpos], name_a))
        return results

    def resolve_names(self, monitors):
        "change partial descriptions used in config for monitor names"
        placement_rules = deepcopy(self.config.get("placement", {}))
        monitors_by_descr = {m["description"]: m for m in monitors}
        cleaned_config: dict[str, dict[str, str]] = {}
        plugged_monitors = {m["name"] for m in monitors}
        for descr1, placement in placement_rules.items():
            mon = self._get_mon_by_pat(descr1, monitors_by_descr)
            if not mon:
                continue
            name1 = mon["name"]
            if name1 not in plugged_monitors:
                continue
            cleaned_config[name1] = {}
            for position, descr_list in placement.items():
                if isinstance(descr_list, str):
                    descr_list = [descr_list]
                resolved = [
                    self._get_mon_by_pat(p, monitors_by_descr)["name"]
                    for p in descr_list
                ]
                if resolved:
                    cleaned_config[name1][clean_pos(position)] = [
                        r for r in resolved if r in plugged_monitors
                    ]
        return cleaned_config
