" The monitors plugin "
import asyncio
import subprocess
from typing import Any, cast

from ..ipc import hyprctlJSON
from .interface import Plugin


def configure_monitors(monitors, screenid: str, pos_x: int, pos_y: int) -> None:
    "Apply the configuration change"
    x_offset = -pos_x if pos_x < 0 else 0
    y_offset = -pos_y if pos_y < 0 else 0

    min_x = pos_x
    min_y = pos_y

    command = ["wlr-randr"]
    other_monitors = [mon for mon in monitors if mon["name"] != screenid]
    for mon in other_monitors:
        min_x = min(min_x, mon["x"])
        min_y = min(min_y, mon["y"])
    x_offset = -min_x
    y_offset = -min_y
    for mon in other_monitors:
        command.extend(
            [
                "--output",
                mon["name"],
                "--pos",
                f"{mon['x']+x_offset},{mon['y']+y_offset}",
            ]
        )

    command.extend(
        ["--output", screenid, "--pos", f"{pos_x+x_offset},{pos_y+y_offset}"]
    )
    subprocess.call(command)


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    async def load_config(self, config) -> None:
        await super().load_config(config)
        await self.run_relayout()

    async def run_relayout(self):
        "Recompute & apply every monitors's layout"
        monitors = cast(list[dict], await hyprctlJSON("monitors"))
        for monitor in monitors:
            await self.event_monitoradded(
                monitor["name"], no_default=True, monitors=monitors
            )

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
                mon_description = mon["description"]
                break
        else:
            self.log.info("Monitor %s not found", monitor_name)
            return

        if self._place_monitors(monitor_name, mon_description, monitors):
            return

        if not no_default:
            default_command = self.config.get("unknown")
            if default_command:
                await asyncio.create_subprocess_shell(default_command)

    def _place_monitors(
        self, monitor_name: str, mon_description: str, monitors: list[dict[str, Any]]
    ):
        "place a given monitor according to config"
        mon_by_name = {m["name"]: m for m in monitors}
        newmon = mon_by_name[monitor_name]
        for mon_pattern, conf in self.config["placement"].items():
            if mon_pattern in mon_description:
                for placement, other_mon_description in conf.items():
                    ref = mon_by_name.get(other_mon_description)
                    if ref is None or monitor_name == other_mon_description:
                        continue
                    if ref:
                        place = placement.lower()
                        x: int = 0
                        y: int = 0
                        if place == "topof":
                            x = ref["x"]
                            y = ref["y"] - newmon["height"]
                        elif place == "bottomof":
                            x = ref["x"]
                            y = ref["y"] + ref["height"]
                        elif place == "leftof":
                            x = ref["x"] - newmon["width"]
                            y = ref["y"]
                        else:  # rightof
                            x = ref["x"] + ref["width"]
                            y = ref["y"]

                        self.log.info("Will place %s @ %s,%s", monitor_name, x, y)
                        configure_monitors(monitors, monitor_name, x, y)
                        return True
        return False
