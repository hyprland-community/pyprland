"""The monitors plugin."""

import asyncio
from typing import Any, ClassVar

from ...adapters.niri import niri_output_to_monitor_info
from ...aioops import DebouncedTask
from ...models import Environment, MonitorInfo, ReloadReason
from ...validation import ConfigField, ConfigItems
from ..interface import Plugin
from .commands import (
    build_hyprland_command,
    build_niri_disable_action,
    build_niri_position_action,
    build_niri_scale_action,
    build_niri_transform_action,
)
from .layout import (
    build_graph,
    compute_positions,
    find_cycle_path,
)
from .resolution import get_monitor_by_pattern, resolve_placement_config
from .schema import MONITOR_PROPS_SCHEMA, validate_placement_keys


class Extension(Plugin):
    """Allows relative placement and configuration of monitors."""

    environments: ClassVar[list[Environment]] = [Environment.HYPRLAND, Environment.NIRI]

    config_schema = ConfigItems(
        ConfigField("startup_relayout", bool, default=True, description="Relayout monitors on startup", category="behavior"),
        ConfigField(
            "relayout_on_config_change", bool, default=True, description="Relayout when Hyprland config is reloaded", category="behavior"
        ),
        ConfigField(
            "new_monitor_delay", float, default=1.0, description="Delay in seconds before handling new monitor", category="behavior"
        ),
        ConfigField(
            "unknown", str, default="", description="Command to run when an unknown monitor is detected", category="external_commands"
        ),
        ConfigField(
            "placement",
            dict,
            required=True,
            default={},
            description="Monitor placement rules (pattern -> positioning rules)",
            children=MONITOR_PROPS_SCHEMA,
            validator=validate_placement_keys,
            children_allow_extra=True,  # Allow dynamic placement keys (leftOf, topOf, etc.)
            category="placement",
        ),
        ConfigField(
            "hotplug_commands",
            dict,
            default={},
            description="Commands to run when specific monitors are plugged (pattern -> command)",
            category="external_commands",
        ),
        ConfigField(
            "hotplug_command", str, default="", description="Command to run when any monitor is plugged", category="external_commands"
        ),
    )

    _mon_by_pat_cache: dict[str, MonitorInfo]
    _relayout_debouncer: DebouncedTask

    async def on_reload(self, reason: ReloadReason = ReloadReason.RELOAD) -> None:
        """Reload the plugin."""
        _ = reason  # unused
        self._mon_by_pat_cache = {}
        self._relayout_debouncer = DebouncedTask(ignore_window=3.0)
        self._clear_mon_by_pat_cache()
        monitors = await self.backend.get_monitors(include_disabled=True)

        for mon in self.state.monitors:
            await self._hotplug_command(monitors, name=mon)

        if self.get_config_bool("startup_relayout"):

            async def _delayed_relayout() -> None:
                await self._run_relayout(monitors)
                await asyncio.sleep(1)
                await self._run_relayout()

            await _delayed_relayout()

    async def event_configreloaded(self, _: str = "") -> None:
        """Relayout screens after settings has been lost."""
        if not self.get_config_bool("relayout_on_config_change"):
            return
        self._relayout_debouncer.schedule(self._delayed_relayout, delay=1.0)

    async def _delayed_relayout(self) -> None:
        """Delayed relayout that runs twice with 1s gap."""
        for _i in range(2):
            await asyncio.sleep(1)
            await self._run_relayout()

    async def event_monitoradded(self, name: str) -> None:
        """Triggers when a monitor is plugged.

        Args:
            name: The name of the added monitor
        """
        delay = self.get_config_float("new_monitor_delay")
        await asyncio.sleep(delay)
        monitors = await self.backend.get_monitors(include_disabled=True)
        await self._hotplug_command(monitors, name)

        if not await self._run_relayout(monitors):
            default_command = self.get_config_str("unknown")
            if default_command:
                await asyncio.create_subprocess_shell(default_command)

    async def niri_outputschanged(self, _data: dict) -> None:
        """Handle Niri output changes.

        Args:
            _data: Event data from Niri (unused)
        """
        delay = self.get_config_float("new_monitor_delay")
        await asyncio.sleep(delay)
        await self._run_relayout()

    async def run_relayout(self) -> bool:
        """Recompute & apply every monitors's layout."""
        return await self._run_relayout()

    async def _run_relayout(self, monitors: list[MonitorInfo] | None = None) -> bool:
        """Recompute & apply every monitors's layout.

        Args:
            monitors: Optional list of monitors to use. If not provided, fetches current state.
        """
        if self.state.environment == Environment.NIRI:
            return await self._run_relayout_niri()

        if monitors is None:
            monitors = await self.backend.get_monitors(include_disabled=True)

        self._clear_mon_by_pat_cache()

        # 1. Resolve configuration
        config = self._resolve_names(monitors)
        if not config:
            self.log.debug("No configuration item is applicable")
            return False

        self.log.debug("Using %s", config)

        monitors_by_name = {m["name"]: m for m in monitors}

        # Mark monitors to disable and get enabled monitors
        enabled_monitors_by_name = self._mark_disabled_monitors(config, monitors_by_name)

        # 2. Build dependency graph
        tree, in_degree = self._build_graph(config, enabled_monitors_by_name)

        # 3. Compute Layout
        positions = self._compute_positions(enabled_monitors_by_name, tree, in_degree, config)

        # 4 & 5. Normalize and Apply
        return await self._apply_layout(positions, monitors_by_name, config)

    async def _run_relayout_niri(self) -> bool:
        """Niri implementation of relayout."""
        outputs = await self.backend.execute_json("outputs")

        monitors: list[MonitorInfo] = [niri_output_to_monitor_info(name, data) for name, data in outputs.items()]

        self._clear_mon_by_pat_cache()

        # 1. Resolve configuration
        config = self._resolve_names(monitors)
        if not config:
            self.log.debug("No configuration item is applicable")
            return False

        monitors_by_name = {m["name"]: m for m in monitors}

        # Mark monitors to disable and get enabled monitors
        enabled_monitors_by_name = self._mark_disabled_monitors(config, monitors_by_name)

        # 2. Build dependency graph
        tree, in_degree = self._build_graph(config, enabled_monitors_by_name)

        # 3. Compute Layout
        positions = self._compute_positions(enabled_monitors_by_name, tree, in_degree, config)

        # 4 & 5. Apply
        return await self._apply_layout(positions, monitors_by_name, config)

    def _mark_disabled_monitors(
        self,
        config: dict[str, Any],
        monitors_by_name: dict[str, MonitorInfo],
    ) -> dict[str, MonitorInfo]:
        """Mark monitors to disable and return enabled monitors.

        Args:
            config: Configuration dictionary containing optional 'disables' lists
            monitors_by_name: Mapping of monitor names to info (modified in-place)

        Returns:
            Dictionary of enabled monitors (excludes those marked to_disable)
        """
        monitors_to_disable: set[str] = set()
        for cfg in config.values():
            if "disables" in cfg:
                monitors_to_disable.update(cfg["disables"])

        for name in monitors_to_disable:
            if name in monitors_by_name:
                monitors_by_name[name]["to_disable"] = True

        return {k: v for k, v in monitors_by_name.items() if not v.get("to_disable")}

    def _build_graph(
        self, config: dict[str, Any], monitors_by_name: dict[str, MonitorInfo]
    ) -> tuple[dict[str, list[tuple[str, str]]], dict[str, int]]:
        """Build the dependency graph for monitor layout.

        Args:
            config: Configuration dictionary
            monitors_by_name: Mapping of monitor names to info
        """
        tree, in_degree, multi_target_info = build_graph(config, monitors_by_name)

        # Log warnings for multiple targets
        for name, rule_name, target_names in multi_target_info:
            self.log.debug(
                "Multiple targets for %s.%s: %s - using first: %s",
                name,
                rule_name,
                target_names,
                target_names[0],
            )

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
        positions, unprocessed = compute_positions(monitors_by_name, tree, in_degree, config)

        # Check for unprocessed monitors (indicates circular dependencies)
        if unprocessed:
            cycle_info = find_cycle_path(config, unprocessed)
            self.log.warning(
                "Circular dependency detected: %s. Ensure at least one monitor has no placement rule (anchor).",
                cycle_info,
            )

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

        if self.state.environment == Environment.NIRI:
            return await self._apply_niri_layout(positions, monitors_by_name, config)

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
            cmd = build_hyprland_command(mon, mon_config)
            cmds.append(cmd)

        for name, mon in monitors_by_name.items():
            if mon.get("to_disable"):
                cmds.append(f"monitor {name},disable")

        # Set ignore window before triggering config reload via hyprctl keyword
        self._relayout_debouncer.set_ignore_window()

        for cmd in cmds:
            self.log.debug(cmd)
            await self.backend.execute(cmd, base_command="keyword")
        return True

    async def _apply_niri_layout(
        self,
        positions: dict[str, tuple[int, int]],
        monitors_by_name: dict[str, MonitorInfo],
        config: dict[str, Any],
    ) -> bool:
        """Apply Niri layout.

        Args:
            positions: Computed (x, y) positions for each monitor
            monitors_by_name: Mapping of monitor names to info
            config: Configuration dictionary
        """
        # Handle disabled monitors first
        for name, mon in monitors_by_name.items():
            if mon.get("to_disable"):
                await self.backend.execute(build_niri_disable_action(name))

        # Apply positions and settings for enabled monitors
        for name, (x, y) in positions.items():
            # Set position
            await self.backend.execute(build_niri_position_action(name, x, y))

            mon_config = config.get(name, {})

            # Set scale if configured
            scale = mon_config.get("scale")
            if scale:
                await self.backend.execute(build_niri_scale_action(name, scale))

            # Set transform if configured
            transform = mon_config.get("transform")
            if transform is not None:
                await self.backend.execute(build_niri_transform_action(name, transform))

        return True

    def _resolve_names(self, monitors: list[MonitorInfo]) -> dict[str, Any]:
        """Resolve configuration patterns to actual monitor names.

        Args:
            monitors: List of available monitors
        """
        return resolve_placement_config(
            self.get_config_dict("placement"),
            monitors,
            self._mon_by_pat_cache,
        )

    async def _hotplug_command(self, monitors: list[MonitorInfo], name: str) -> None:
        """Run the hotplug command for the monitor.

        Args:
            monitors: List of available monitors
            name: Name of the hotplugged monitor
        """
        monitors_by_descr = {m["description"]: m for m in monitors}
        monitors_by_name = {m["name"]: m for m in monitors}
        for descr, command in self.get_config_dict("hotplug_commands").items():
            mon = get_monitor_by_pattern(descr, monitors_by_descr, monitors_by_name, self._mon_by_pat_cache)
            if mon and mon["name"] == name:
                await asyncio.create_subprocess_shell(command)
                break
        single_command = self.get_config_str("hotplug_command")
        if single_command:
            await asyncio.create_subprocess_shell(single_command)

    def _clear_mon_by_pat_cache(self) -> None:
        """Clear the cache."""
        self._mon_by_pat_cache = {}
