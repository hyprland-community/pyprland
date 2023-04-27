from typing import Any
from .interface import Plugin
import subprocess

from ..ipc import hyprctlJSON


class Extension(Plugin):
    async def event_monitoradded(self, screenid):
        screenid = screenid.strip()

        monitors: list[dict[str, Any]] = await hyprctlJSON("monitors")
        for mon in monitors:
            if mon["name"].startswith(screenid):
                mon_name = mon["description"]
                break
        else:
            print(f"Monitor {screenid} not found")
            return

        mon_by_name = {m["name"]: m for m in monitors}

        newmon = mon_by_name[screenid]

        for mon_pattern, conf in self.config["placement"].items():
            if mon_pattern in mon_name:
                for placement, mon_name in conf.items():
                    ref = mon_by_name[mon_name]
                    if ref:
                        place = placement.lower()
                        if place == "topof":
                            x: int = ref["x"]
                            y: int = ref["y"] - newmon["height"]
                        elif place == "bottomof":
                            x: int = ref["x"]
                            y: int = ref["y"] + ref["height"]
                        elif place == "leftof":
                            x: int = ref["x"] - newmon["width"]
                            y: int = ref["y"]
                        else:  # rightof
                            x: int = ref["x"] + ref["width"]
                            y: int = ref["y"]
                        subprocess.call(
                            ["wlr-randr", "--output", screenid, "--pos", f"{x},{y}"]
                        )
