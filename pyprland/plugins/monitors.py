" The monitors plugin "
import asyncio
import subprocess
from typing import Any, cast

from ..ipc import hyprctlJSON
from .interface import Plugin


def get_XY(place, main_mon, other_mon):  # pylint: disable=too-many-return-statements
    "returns (x, y) position of `main_mon` to set it at `place` regarding `other_mon`"
    if place == "topof":
        return (
            other_mon["x"],
            other_mon["y"] - int(main_mon["height"] / main_mon["scale"]),
        )
    if place == "bottomof":
        return (
            other_mon["x"],
            other_mon["y"] + int(other_mon["height"] / other_mon["scale"]),
        )
    if place == "leftof":
        return (
            other_mon["x"] - int(main_mon["width"] / main_mon["scale"]),
            other_mon["y"],
        )
    if place == "rightof":
        return (
            other_mon["x"] + int(other_mon["width"] / other_mon["scale"]),
            other_mon["y"],
        )
    # Handle <position>MiddleOf
    if place == "topmiddleof":
        return (
            other_mon["x"] + int((other_mon["width"] - main_mon["width"]) / 2),
            other_mon["y"] - int(main_mon["height"] / main_mon["scale"]),
        )
    if place == "bottommiddleof":
        return (
            other_mon["x"] + int((other_mon["width"] - main_mon["width"]) / 2),
            other_mon["y"] + int(other_mon["height"] / other_mon["scale"]),
        )
    if place == "leftmiddleof":
        return (
            other_mon["x"] - int(main_mon["width"] / main_mon["scale"]),
            other_mon["y"] + int((other_mon["height"] - main_mon["height"]) / 2),
        )
    if place == "rightmiddleof":
        return (
            other_mon["x"] + int(other_mon["width"] / other_mon["scale"]),
            other_mon["y"] + int((other_mon["height"] - main_mon["height"]) / 2),
        )
    # Handle <position>EndOf
    if place == "topendof":
        return (
            other_mon["x"] + int((other_mon["width"] - main_mon["width"])),
            other_mon["y"] - int(main_mon["height"] / main_mon["scale"]),
        )
    if place == "bottomendof":
        return (
            other_mon["x"] + int((other_mon["width"] - main_mon["width"])),
            other_mon["y"] + int(other_mon["height"] / other_mon["scale"]),
        )
    if place == "leftendof":
        return (
            other_mon["x"] - int(main_mon["width"] / main_mon["scale"]),
            other_mon["y"] + int((other_mon["height"] - main_mon["height"])),
        )
    if place == "rightendof":
        return (
            other_mon["x"] + int(other_mon["width"] / other_mon["scale"]),
            other_mon["y"] + int((other_mon["height"] - main_mon["height"])),
        )
    return None


def configure_monitors(monitors, screenid: str, pos_x: int, pos_y: int) -> None:
    "Apply the configuration change"

    command = ["wlr-randr"]
    monitor = [mon for mon in monitors if mon["name"] == screenid][0]

    monitor["x"] = pos_x
    monitor["y"] = pos_y

    command.extend(["--output", screenid, "--pos", f"{pos_x},{pos_y}"])
    subprocess.call(command)


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    _changes_tracker: set | None = None

    _mon_by_pat_cache: dict[str, dict] = {}

    async def load_config(self, config) -> None:
        await super().load_config(config)
        await self.run_relayout()

    async def run_relayout(self):
        "Recompute & apply every monitors's layout"
        monitors = cast(list[dict], await hyprctlJSON("monitors"))
        self._changes_tracker = set()
        for monitor in monitors:
            if monitor["name"] not in self._changes_tracker:
                await self.event_monitoradded(
                    monitor["name"], no_default=True, monitors=monitors
                )
        self._changes_tracker = None

    async def event_monitoradded(
        self, monitor_name, no_default=False, monitors: list | None = None
    ) -> None:
        "Triggers when a monitor is plugged"
        monitor_name = monitor_name.strip()

        if not monitors:
            monitors = cast(list, await hyprctlJSON("monitors"))

        assert monitors

        for mon in monitors:
            if mon["name"].startswith(monitor_name):
                mon_info = mon
                break
        else:
            self.log.warning("Monitor %s not found", monitor_name)
            return

        if self._place_monitors(mon_info, monitors):
            return

        if not no_default:
            default_command = self.config.get("unknown")
            if default_command:
                await asyncio.create_subprocess_shell(default_command)

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
        "topendof": "bottomendof",
        "bottomendof": "topendof",
        "leftendof": "rightendof",
        "rightendof": "leftendof",
    }

    def _get_rules(self, mon_description):
        "build a list of matching rules from the config"
        for pattern, config in self.config["placement"].items():
            matched = pattern in mon_description
            for position, descr_list in config.items():
                for descr in descr_list:
                    lp = position.lower()
                    if matched or mon_description in descr:
                        yield (
                            lp if matched else self._flipped_positions[lp],
                            descr,
                            f"{pattern} {config}",
                        )

    def _place_monitors(
        self,
        mon_info: dict[str, int | float | str | list],
        monitors: list[dict[str, Any]],
    ):
        "place a given monitor according to config"

        mon_name: str = cast(str, mon_info["name"])
        monitors_by_descr = {m["description"]: m for m in monitors}
        self._clear_mon_by_pat_cache()
        matched = False

        for place, other_screen, rule in self._get_rules(mon_info["description"]):
            main_mon = mon_info
            other_mon = self._get_mon_by_pat(other_screen, monitors_by_descr)

            if other_mon and main_mon:
                matched = True
                try:
                    x, y = get_XY(place, main_mon, other_mon)
                except TypeError:
                    self.log.error("Unknown position type: %s (%s)", place, rule)
                else:
                    self.log.info("Will place %s @ %s,%s (%s)", mon_name, x, y, rule)
                configure_monitors(monitors, mon_name, x, y)

                if self._changes_tracker is not None:
                    self._changes_tracker.add(mon_name)
                    # Also prevent the reference screen from moving
                    self._changes_tracker.add(other_mon["name"])

        return matched
