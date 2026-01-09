"""The monitors plugin."""

import asyncio
from collections import defaultdict
from typing import Any, cast

from ...models import MonitorInfo
from ..interface import Plugin
from .layout import MONITOR_PROPS, compute_xy, get_dims


class Extension(Plugin):
    """Control monitors layout."""

    _mon_by_pat_cache: dict[str, MonitorInfo] = {}

    async def on_reload(self) -> None:
        """Reload the plugin."""
        self._clear_mon_by_pat_cache()
        monitors = await self.hyprctl_json("monitors all")

        for mon in self.state.monitors:
            await self._hotplug_command(monitors, name=mon)

        if self.config.get_bool("startup_relayout", True):

            async def _delayed_relayout() -> None:
                await self._run_relayout(monitors)
                await asyncio.sleep(1)
                await self._run_relayout()

            await asyncio.create_task(_delayed_relayout())

    async def event_configreloaded(self, _: str = "") -> None:
        """Relayout screens after settings has been lost."""
        if not self.config.get("relayout_on_config_change", True):
            return
        for _i in range(2):
            await asyncio.sleep(1)
            await self._run_relayout()

    async def event_monitoradded(self, name: str) -> None:
        """Triggers when a monitor is plugged.

        Args:
            name: The name of the added monitor
        """
        await asyncio.sleep(self.config.get("new_monitor_delay", 1.0))
        monitors = await self.hyprctl_json("monitors all")
        await self._hotplug_command(monitors, name)

        if not await self._run_relayout(monitors):
            default_command = self.config.get("unknown")
            if default_command:
                await asyncio.create_subprocess_shell(default_command)

    async def run_relayout(self) -> bool:
        """Recompute & apply every monitors's layout."""
        return await self._run_relayout()

    async def _run_relayout(self, monitors: list[MonitorInfo] | None = None) -> bool:
        """Recompute & apply every monitors's layout.

        Args:
            monitors: Optional list of monitors to use. If not provided, fetches current state.
        """
        if monitors is None:
            monitors = cast("list[MonitorInfo]", await self.hyprctl_json("monitors all"))

        self._clear_mon_by_pat_cache()

        # 1. Resolve configuration
        config = self._resolve_names(monitors)
        if not config:
            self.log.debug("No configuration item is applicable")
            return False

        self.log.debug("Using %s", config)

        monitors_by_name = {m["name"]: m for m in monitors}

        monitors_to_disable = set()
        for cfg in config.values():
            if "disables" in cfg:
                monitors_to_disable.update(cfg["disables"])

        for name in monitors_to_disable:
            if name in monitors_by_name:
                monitors_by_name[name]["to_disable"] = True

        enabled_monitors_by_name = {k: v for k, v in monitors_by_name.items() if not v.get("to_disable")}

        # 2. Build dependency graph
        tree, in_degree = self._build_graph(config, enabled_monitors_by_name)

        # 3. Compute Layout
        positions = self._compute_positions(enabled_monitors_by_name, tree, in_degree, config)

        # 4 & 5. Normalize and Apply
        return await self._apply_layout(positions, monitors_by_name, config)

    def _build_graph(
        self, config: dict[str, Any], monitors_by_name: dict[str, MonitorInfo]
    ) -> tuple[dict[str, list[tuple[str, str]]], dict[str, int]]:
        """Build the dependency graph for monitor layout.

        Args:
            config: Configuration dictionary
            monitors_by_name: Mapping of monitor names to info
        """
        tree: dict[str, list[tuple[str, str]]] = defaultdict(list)
        in_degree: dict[str, int] = defaultdict(int)

        for name in monitors_by_name:
            in_degree[name] = 0

        for name, rules in config.items():
            for rule_name, target_names in rules.items():
                if rule_name in MONITOR_PROPS or rule_name == "disables":
                    continue
                target_name = target_names[0] if target_names else None
                if target_name and target_name in monitors_by_name:
                    tree[target_name].append((name, rule_name))
                    in_degree[name] += 1
        return tree, in_degree

    def _compute_positions(
        self,
        monitors_by_name: dict[str, MonitorInfo],
        tree: dict[str, list[tuple[str, str]]],
        in_degree: dict[str, int],
        config: dict[str, Any],
    ) -> dict[str, tuple[int, int]]:
        """Compute the positions of all monitors.

        Args:
            monitors_by_name: Mapping of monitor names to info
            tree: Dependency graph
            in_degree: In-degree of each node in the graph
            config: Configuration dictionary
        """
        queue = [name for name in monitors_by_name if in_degree[name] == 0]
        positions: dict[str, tuple[int, int]] = {}
        for name in queue:
            positions[name] = (monitors_by_name[name]["x"], monitors_by_name[name]["y"])

        processed = set()
        while queue:
            ref_name = queue.pop(0)
            if ref_name in processed:
                continue
            processed.add(ref_name)

            for child_name, rule in tree[ref_name]:
                ref_rect = (
                    *positions[ref_name],
                    *get_dims(monitors_by_name[ref_name], config.get(ref_name, {})),
                )

                mon_dim = get_dims(monitors_by_name[child_name], config.get(child_name, {}))

                positions[child_name] = compute_xy(
                    ref_rect,
                    mon_dim,
                    rule,
                )

                in_degree[child_name] -= 1
                if in_degree[child_name] == 0:
                    queue.append(child_name)
        return positions

    async def _apply_layout(
        self,
        positions: dict[str, tuple[int, int]],
        monitors_by_name: dict[str, MonitorInfo],
        config: dict[str, Any],
    ) -> bool:
        """Apply the computed layout.

        Args:
            positions: Computed (x, y) positions for each monitor
            monitors_by_name: Mapping of monitor names to info
            config: Configuration dictionary
        """
        has_disabled = any(m.get("to_disable") for m in monitors_by_name.values())
        if not positions and not has_disabled:
            return False

        if positions:
            min_x = min(x for x, y in positions.values())
            min_y = min(y for x, y in positions.values())
        else:
            min_x = 0
            min_y = 0

        cmds = []
        for name, (x, y) in positions.items():
            mon = monitors_by_name[name]
            mon["x"] = x - min_x
            mon["y"] = y - min_y
            mon_config = config.get(name, {})
            cmd = self._build_monitor_command(mon, mon_config)
            cmds.append(cmd)

        for name, mon in monitors_by_name.items():
            if mon.get("to_disable"):
                cmds.append(f"monitor {name},disable")

        for cmd in cmds:
            self.log.debug(cmd)
            await self.hyprctl(cmd, "keyword")
        return True

    def _build_monitor_command(self, monitor: MonitorInfo, config: dict[str, Any]) -> str:
        """Build the monitor command.

        Args:
            monitor: Monitor information
            config: Configuration for the monitor
        """
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
        """Resolve configuration patterns to actual monitor names.

        Args:
            monitors: List of available monitors
        """
        monitors_by_descr = {m["description"]: m for m in monitors}
        monitors_by_name = {m["name"]: m for m in monitors}

        cleaned_config: dict[str, dict[str, Any]] = {}

        for pat, rules in self.config.get("placement", {}).items():
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
        """Run the hotplug command for the monitor.

        Args:
            monitors: List of available monitors
            name: Name of the hotplugged monitor
        """
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
        """Return a (plugged) monitor object given its pattern or none if not found.

        Args:
            pat: Pattern to search for
            description_db: Database of monitors by description
            name_db: Database of monitors by name
        """
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
