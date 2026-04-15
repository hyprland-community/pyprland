"""stash allows storing named single-window overlays."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, cast

from ..adapters.units import convert_coords
from ..models import Environment, ReloadReason
from ..validation import ConfigField, ConfigItems, ConfigValidator
from .interface import Plugin

STASH_PREFIX = "st-"
PAIR_SIZE = 2

STASH_SECTION_SCHEMA = ConfigItems(
    ConfigField("animation", str, default="", description="Reserved animation setting", category="basic"),
    ConfigField("size", str, required=True, description="Overlay size like '24% 54%'", category="positioning"),
    ConfigField("position", str, required=True, description="Overlay position like '76% 22%'", category="positioning"),
    ConfigField("preserve_aspect", bool, default=False, description="Keep size and position across shows", category="behavior"),
)


@dataclass
class StashDefinition:
    """User-defined stash properties."""

    name: str
    animation: str
    size: str
    position: str
    preserve_aspect: bool


@dataclass
class StashSlot:
    """Runtime state for a single stash."""

    definition: StashDefinition
    address: str = ""
    was_floating: bool = True
    visible: bool = False
    saved_size: tuple[int, int] | None = None
    saved_offset: tuple[int, int] | None = None

    @property
    def workspace(self) -> str:
        """Return the hidden workspace backing this stash."""
        return f"special:{STASH_PREFIX}{self.definition.name}"

    @property
    def occupied(self) -> bool:
        """Return whether this stash currently owns a window."""
        return bool(self.address)


class Extension(Plugin, environments=[Environment.HYPRLAND]):
    """Manage named single-window stashes as pinned overlays."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._slots: dict[str, StashSlot] = {}
        self._addr_to_stash: dict[str, str] = {}

    def validate_config(self) -> list[str]:
        """Validate nested stash sections."""
        return self._validate_stash_config(self.name, dict(self.config))

    @classmethod
    def validate_config_static(cls, plugin_name: str, config: dict) -> list[str]:
        """Validate nested stash sections without instantiating the plugin."""
        return cls._validate_stash_config(plugin_name, config)

    @classmethod
    def _validate_stash_config(cls, plugin_name: str, config: dict) -> list[str]:
        log_name = f"pyprland.plugins.{plugin_name}"
        validator = ConfigValidator(config, plugin_name, logging.getLogger(log_name))
        errors: list[str] = []
        for stash_name, stash_config in config.items():
            if not isinstance(stash_config, dict):
                errors.append(f"[{plugin_name}] section '{stash_name}' must be a table")
                continue
            child_prefix = f"{plugin_name}.{stash_name}"
            child_validator = ConfigValidator(stash_config, child_prefix, validator.log)
            errors.extend(child_validator.validate(STASH_SECTION_SCHEMA))
            errors.extend(child_validator.warn_unknown_keys(STASH_SECTION_SCHEMA))
        return errors

    async def on_reload(self, reason: ReloadReason = ReloadReason.RELOAD) -> None:  # noqa: ARG002
        """Refresh configured stash definitions."""
        self._load_stash_definitions()

    async def exit(self) -> None:
        """Best-effort release of stashed windows during clean shutdown."""
        for slot in self._slots.values():
            if slot.occupied:
                await self._release_slot(slot, workspace=self.state.active_workspace, focus=False)

    async def event_closewindow(self, addr: str) -> None:
        """Remove closed windows from stash tracking."""
        address = "0x" + addr
        stash_name = self._addr_to_stash.pop(address, "")
        if not stash_name:
            return
        slot = self._slots.get(stash_name)
        if slot is None or slot.address != address:
            return
        self._clear_slot(slot)

    async def run_stash_send(self, name: str) -> None:
        """<name> Send the focused window to stash <name>, or release it if already focused there."""
        slot = self._require_slot(name)
        active = await self._get_active_window()
        addr = active.get("address", "")
        if not addr:
            return

        current_stash = self._addr_to_stash.get(addr)
        if current_stash == name:
            await self._release_slot(slot, workspace=self.state.active_workspace)
            return

        if current_stash:
            await self._detach_from_stash(self._slots[current_stash], keep_floating=True)

        if slot.occupied:
            await self._release_slot(slot, workspace=self.state.active_workspace, focus=False)

        await self._stash_window(slot, active)

    async def run_stash_toggle(self, name: str) -> None:
        """<name> Show or hide the named stash overlay."""
        slot = self._require_slot(name)
        if not slot.occupied:
            return
        if slot.visible:
            await self._hide_slot(slot)
        else:
            await self._show_slot(slot)

    def _load_stash_definitions(self) -> None:
        previous = self._slots
        self._slots = {}

        for stash_name, stash_config in self.config.iter_subsections():
            slot = previous.get(stash_name)
            definition = StashDefinition(
                name=stash_name,
                animation=str(stash_config.get("animation", "")),
                size=str(stash_config["size"]),
                position=str(stash_config["position"]),
                preserve_aspect=bool(stash_config.get("preserve_aspect", False)),
            )
            if slot is None:
                slot = StashSlot(definition=definition)
            else:
                slot.definition = definition
            self._slots[stash_name] = slot

    def _require_slot(self, name: str) -> StashSlot:
        if name not in self._slots:
            self._load_stash_definitions()
        try:
            return self._slots[name]
        except KeyError as e:
            msg = f"Unknown stash '{name}'"
            raise ValueError(msg) from e

    async def _get_active_window(self) -> dict[str, Any]:
        return cast("dict[str, Any]", await self.backend.execute_json("activewindow"))

    async def _stash_window(self, slot: StashSlot, active: dict[str, Any]) -> None:
        addr = cast("str", active["address"])
        slot.address = addr
        slot.was_floating = bool(active.get("floating", False))
        slot.visible = False
        self._addr_to_stash[addr] = slot.definition.name

        await self.backend.move_window_to_workspace(addr, slot.workspace, silent=True)
        if not slot.was_floating:
            await self.backend.toggle_floating(addr)

    async def _show_slot(self, slot: StashSlot) -> None:
        if not slot.occupied:
            return

        await self.backend.move_window_to_workspace(slot.address, self.state.active_workspace, silent=True)
        await self._apply_geometry(slot)
        await self.backend.pin_window(slot.address)
        await self.backend.focus_window(slot.address)
        slot.visible = True

    async def _hide_slot(self, slot: StashSlot) -> None:
        if not slot.occupied:
            return

        await self._capture_geometry(slot)
        if slot.visible:
            await self.backend.pin_window(slot.address)
        await self.backend.move_window_to_workspace(slot.address, slot.workspace, silent=True)
        slot.visible = False

    async def _release_slot(self, slot: StashSlot, workspace: str, *, focus: bool = True) -> None:
        if not slot.occupied:
            return

        addr = slot.address
        if slot.visible:
            await self.backend.pin_window(addr)
        await self.backend.move_window_to_workspace(addr, workspace, silent=True)
        await self._restore_floating(slot)
        if focus:
            await self.backend.focus_window(addr)
        self._clear_slot(slot)

    async def _detach_from_stash(self, slot: StashSlot, *, keep_floating: bool) -> None:
        if not slot.occupied:
            return

        if slot.visible:
            await self.backend.pin_window(slot.address)
        if not keep_floating:
            await self._restore_floating(slot)
        self._clear_slot(slot)

    async def _restore_floating(self, slot: StashSlot) -> None:
        if slot.was_floating:
            return
        await self.backend.toggle_floating(slot.address)

    def _clear_slot(self, slot: StashSlot) -> None:
        if slot.address:
            self._addr_to_stash.pop(slot.address, None)
        slot.address = ""
        slot.visible = False
        slot.was_floating = True
        slot.saved_size = None
        slot.saved_offset = None

    async def _capture_geometry(self, slot: StashSlot) -> None:
        if not slot.definition.preserve_aspect:
            return

        client = await self.backend.get_client_props(addr=slot.address)
        if client is None:
            return

        size = client.get("size")
        position = client.get("at")
        if not isinstance(size, (list, tuple)) or len(size) != PAIR_SIZE:
            return
        if not isinstance(position, (list, tuple)) or len(position) != PAIR_SIZE:
            return

        slot.saved_size = (int(size[0]), int(size[1]))

        monitor = await self.get_focused_monitor_or_warn("stash geometry save")
        if monitor is None:
            slot.saved_offset = (int(position[0]), int(position[1]))
            return

        base_x = int(monitor["x"] / monitor["scale"])
        base_y = int(monitor["y"] / monitor["scale"])
        slot.saved_offset = (int(position[0]) - base_x, int(position[1]) - base_y)

    async def _apply_geometry(self, slot: StashSlot) -> None:
        monitor = await self.get_focused_monitor_or_warn("stash geometry")
        if monitor is None:
            return

        base_x = int(monitor["x"] / monitor["scale"])
        base_y = int(monitor["y"] / monitor["scale"])

        if slot.definition.preserve_aspect and slot.saved_size and slot.saved_offset:
            width, height = slot.saved_size
            x = base_x + slot.saved_offset[0]
            y = base_y + slot.saved_offset[1]
        else:
            width, height = convert_coords(slot.definition.size, monitor)
            x, y = convert_coords(slot.definition.position, monitor)
            x += base_x
            y += base_y

        await self.backend.resize_window(slot.address, width, height)
        await self.backend.move_window(slot.address, x, y)
