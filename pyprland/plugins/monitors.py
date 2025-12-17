"""The monitors plugin."""

import asyncio
from collections import defaultdict
from typing import Any, cast

from ..common import CastBoolMixin, is_rotated, state
from ..types import MonitorInfo
from .interface import Plugin

MONITOR_PROPS = {"scale", "transform", "rate", "resolution"}


def get_dims(monitor: MonitorInfo) -> tuple[int, int]:
    """Get the effective width and height of a monitor."""
    width = int(monitor["width"] / monitor["scale"])
    height = int(monitor["height"] / monitor["scale"])
    if is_rotated(monitor):
        return height, width
    return width, height


class Extension(CastBoolMixin, Plugin):
    """Control monitors layout."""

    _mon_by_pat_cache: dict[str, MonitorInfo] = {}

    async def on_reload(self) -> None:
        """Reload the plugin."""
        self._clear_mon_by_pat_cache()
        monitors = await self.hyprctl_json("monitors")

        for mon in state.monitors:
            await self._hotplug_command(monitors, name=mon)

        if self.cast_bool(self.config.get("startup_relayout"), True):

            async def _delayed_relayout() -> None:
                await self._run_relayout(monitors)
                await asyncio.sleep(1)
                await self._run_relayout()

            await asyncio.create_task(_delayed_relayout())

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

    async def run_relayout(self) -> bool:
        """Recompute & apply every monitors's layout."""
        return await self._run_relayout()

    async def _run_relayout(self, monitors: list[MonitorInfo] | None = None) -> bool:
        """Recompute & apply every monitors's layout."""
        if monitors is None:
            monitors = cast("list[MonitorInfo]", await self.hyprctl_json("monitors"))

        self._clear_mon_by_pat_cache()

        # 1. Resolve configuration
        config = self._resolve_names(monitors)
        if not config:
            self.log.debug("No configuration item is applicable")
            return False

        self.log.debug("Using %s", config)

        # 2. Build dependency graph (Parent -> Children)
        monitors_by_name = {m["name"]: m for m in monitors}

        # Adjacency list: parent_name -> list[(child_name, rule)]
        tree: dict[str, list[tuple[str, str]]] = defaultdict(list)
        # Track in-degree to find roots
        in_degree: dict[str, int] = defaultdict(int)

        # Ensure all monitors are in in_degree map
        for name in monitors_by_name:
            in_degree[name] = 0

        for name, rules in config.items():
            for rule_name, target_names in rules.items():
                if rule_name in MONITOR_PROPS:
                    continue

                # We only support one relative placement per monitor for simplicity
                target_name = target_names[0] if target_names else None
                if target_name and target_name in monitors_by_name:
                    tree[target_name].append((name, rule_name))
                    in_degree[name] += 1

        # 3. Compute Layout (BFS/Topological Sort)
        # Start with monitors that have no dependencies (roots)
        queue = [name for name in monitors_by_name if in_degree[name] == 0]

        # Positions: name -> (x, y)
        # Initialize roots with their current position
        positions: dict[str, tuple[int, int]] = {}
        for name in queue:
            positions[name] = (monitors_by_name[name]["x"], monitors_by_name[name]["y"])

        processed = set()

        while queue:
            ref_name = queue.pop(0)
            if ref_name in processed:
                continue
            processed.add(ref_name)

            ref_x, ref_y = positions[ref_name]
            ref_mon = monitors_by_name[ref_name]

            for child_name, rule in tree[ref_name]:
                child_mon = monitors_by_name[child_name]
                x, y = self._compute_xy(ref_mon, child_mon, ref_x, ref_y, rule)
                positions[child_name] = (x, y)

                in_degree[child_name] -= 1
                if in_degree[child_name] == 0:
                    queue.append(child_name)

        # 4. Normalize coordinates
        if not positions:
            return False

        min_x = min(x for x, y in positions.values())
        min_y = min(y for x, y in positions.values())

        # 5. Apply configuration
        cmds = []
        for name, (x, y) in positions.items():
            mon = monitors_by_name[name]
            mon["x"] = x - min_x
            mon["y"] = y - min_y

            # Get specific config for this monitor
            mon_config = config.get(name, {})
            cmd = self._build_monitor_command(mon, mon_config)
            cmds.append(cmd)

        for cmd in cmds:
            self.log.debug(cmd)
            await self.hyprctl(cmd, "keyword")

        return True

    def _compute_xy(self, ref_mon: MonitorInfo, mon: MonitorInfo, ref_x: int, ref_y: int, rule: str) -> tuple[int, int]:
        """Compute position of `mon` relative to `ref_mon` based on `rule`."""
        ref_w, ref_h = get_dims(ref_mon)
        mon_w, mon_h = get_dims(mon)

        rule = rule.lower().replace("_", "").replace("-", "")

        x, y = ref_x, ref_y

        # Direction
        if "left" in rule:
            x = ref_x - mon_w
            # Alignment Y
            if "bottom" in rule:
                y = ref_y + ref_h - mon_h
            elif "center" in rule or "middle" in rule:
                y = ref_y + (ref_h - mon_h) // 2
            # else: align top (default) -> y = ref_y

        elif "right" in rule:
            x = ref_x + ref_w
            # Alignment Y
            if "bottom" in rule:
                y = ref_y + ref_h - mon_h
            elif "center" in rule or "middle" in rule:
                y = ref_y + (ref_h - mon_h) // 2

        elif "top" in rule:
            y = ref_y - mon_h
            # Alignment X
            if "right" in rule:
                x = ref_x + ref_w - mon_w
            elif "center" in rule or "middle" in rule:
                x = ref_x + (ref_w - mon_w) // 2

        elif "bottom" in rule:
            y = ref_y + ref_h
            # Alignment X
            if "right" in rule:
                x = ref_x + ref_w - mon_w
            elif "center" in rule or "middle" in rule:
                x = ref_x + (ref_w - mon_w) // 2

        return int(x), int(y)

    def _build_monitor_command(self, monitor: MonitorInfo, config: dict[str, Any]) -> str:
        """Build the monitor command."""
        name = monitor["name"]
        rate = config.get("rate", monitor["refreshRate"])
        res = config.get("resolution", f"{monitor['width']}x{monitor['height']}")
        if isinstance(res, list):
            res = f"{res[0]}x{res[1]}"
        scale = config.get("scale", monitor["scale"])
        position = f"{monitor['x']}x{monitor['y']}"
        transform = config.get("transform", monitor["transform"])
        return f"monitor {name},{res}@{rate},{position},{scale},transform,{transform}"

    def _resolve_names(self, monitors: list[MonitorInfo]) -> dict[str, Any]:
        """Resolve configuration patterns to actual monitor names."""
        monitors_by_descr = {m["description"]: m for m in monitors}
        monitors_by_name = {m["name"]: m for m in monitors}

        cleaned_config: dict[str, dict[str, Any]] = {}

        placement_config = self.config.get("placement", {})

        for pat, rules in placement_config.items():
            # Find the subject monitor
            mon = self._get_mon_by_pat(pat, monitors_by_descr, monitors_by_name)
            if not mon:
                continue

            name = mon["name"]
            cleaned_config[name] = {}

            for rule_key, rule_val in rules.items():
                if rule_key in MONITOR_PROPS:
                    cleaned_config[name][rule_key] = rule_val
                    continue

                # Resolve target monitors in the rule
                targets = []
                val_list = [rule_val] if isinstance(rule_val, str) else rule_val
                for target_pat in val_list:
                    target_mon = self._get_mon_by_pat(target_pat, monitors_by_descr, monitors_by_name)
                    if target_mon:
                        targets.append(target_mon["name"])

                if targets:
                    cleaned_config[name][rule_key] = targets

        return cleaned_config

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
        self._mon_by_pat_cache = {}

    def _get_mon_by_pat(self, pat: str, description_db: dict[str, MonitorInfo], name_db: dict[str, MonitorInfo]) -> MonitorInfo | None:
        """Return a (plugged) monitor object given its pattern or none if not found."""
        cached = self._mon_by_pat_cache.get(pat)
        if cached:
            return cached

        if pat in name_db:
            cached = name_db[pat]
        else:
            for full_descr, mon in description_db.items():
                if pat in full_descr:
                    cached = mon
                    break

        if cached:
            self._mon_by_pat_cache[pat] = cached
        return cached
