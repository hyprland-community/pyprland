"""Generic Wayland backend using wlr-randr for monitor detection."""

import re
from logging import Logger

from ..models import MonitorInfo
from .fallback import FallbackBackend, make_monitor_info
from .niri import NIRI_TRANSFORM_MAP


class WaylandBackend(FallbackBackend):
    """Generic Wayland backend using wlr-randr for monitor information.

    Provides monitor detection for the wallpapers plugin on wlroots-based
    compositors (Sway, etc.). Does not support window management, events,
    or other compositor features.
    """

    @classmethod
    async def is_available(cls) -> bool:
        """Check if wlr-randr is available.

        Returns:
            True if wlr-randr command works
        """
        return await cls._check_command("wlr-randr")

    async def get_monitors(self, *, log: Logger, include_disabled: bool = False) -> list[MonitorInfo]:
        """Get monitor information from wlr-randr.

        Args:
            log: Logger to use for this operation
            include_disabled: If True, include disabled monitors

        Returns:
            List of MonitorInfo dicts
        """
        return await self._run_monitor_command(
            "wlr-randr",
            "wlr-randr",
            self._parse_wlr_randr_output,
            include_disabled=include_disabled,
            log=log,
        )

    def _parse_wlr_randr_output(self, output: str, include_disabled: bool, log: Logger) -> list[MonitorInfo]:
        """Parse wlr-randr output to extract monitor information.

        Example wlr-randr output:
            DP-1 "Dell Inc. DELL U2415 ABC123"
              Enabled: yes
              Modes:
                1920x1200 px, 59.950 Hz (preferred, current)
                1920x1080 px, 60.000 Hz
              Position: 0,0
              Transform: normal
              Scale: 1.000000
            HDMI-A-1 "Some Monitor"
              Enabled: no
              ...

        Args:
            output: Raw wlr-randr output
            include_disabled: Whether to include disabled outputs
            log: Logger for debug output

        Returns:
            List of MonitorInfo dicts
        """
        monitors: list[MonitorInfo] = []

        # Split into sections per output (each starts with output name at column 0)
        sections = re.split(r"^(?=\S)", output, flags=re.MULTILINE)

        for raw_section in sections:
            section = raw_section.strip()
            if not section:
                continue

            monitor = self._parse_output_section(section, len(monitors), log)
            if monitor is None:
                continue

            # Skip disabled unless requested
            if monitor.get("disabled") and not include_disabled:
                continue

            monitors.append(monitor)

        return monitors

    def _parse_output_section(  # noqa: C901  # pylint: disable=too-many-locals
        self, section: str, index: int, log: Logger
    ) -> MonitorInfo | None:
        """Parse a single output section from wlr-randr.

        Args:
            section: Section text for one output
            index: Index for this monitor
            log: Logger for debug output

        Returns:
            MonitorInfo dict or None if parsing failed
        """
        lines = section.splitlines()
        if not lines:
            return None

        # First line: output name and description
        # Format: "DP-1 "Dell Inc. DELL U2415 ABC123""
        header_match = re.match(r'^(\S+)\s*(?:"(.+)")?', lines[0])
        if not header_match:
            return None

        name = header_match.group(1)
        description = header_match.group(2) or name

        # Parse properties
        enabled = True
        width, height = 0, 0
        x, y = 0, 0
        scale = 1.0
        transform = 0
        refresh_rate = 60.0

        for raw_line in lines[1:]:
            line = raw_line.strip()

            # Enabled: yes/no
            if line.startswith("Enabled:"):
                enabled = "yes" in line.lower()

            # Position: x,y
            elif line.startswith("Position:"):
                pos_match = re.search(r"(\d+),\s*(\d+)", line)
                if pos_match:
                    x, y = int(pos_match.group(1)), int(pos_match.group(2))

            # Transform: normal/90/180/270/flipped/etc
            elif line.startswith("Transform:"):
                transform_str = line.split(":", 1)[1].strip()
                transform = NIRI_TRANSFORM_MAP.get(transform_str, 0)

            # Scale: 1.000000
            elif line.startswith("Scale:"):
                try:
                    scale = float(line.split(":", 1)[1].strip())
                except ValueError:
                    scale = 1.0

            # Mode line with "current": 1920x1200 px, 59.950 Hz (preferred, current)
            elif "current" in line.lower() and "x" in line:
                mode_match = re.match(r"(\d+)x(\d+)\s*px,\s*([\d.]+)\s*Hz", line)
                if mode_match:
                    width = int(mode_match.group(1))
                    height = int(mode_match.group(2))
                    refresh_rate = float(mode_match.group(3))

        # Skip outputs without resolution
        if width == 0 or height == 0:
            log.debug("wlr-randr: skipping %s (no active mode)", name)
            return None

        log.debug("wlr-randr monitor: %s %dx%d+%d+%d scale=%.2f transform=%d", name, width, height, x, y, scale, transform)

        return make_monitor_info(
            index=index,
            name=name,
            width=width,
            height=height,
            pos_x=x,
            pos_y=y,
            scale=scale,
            transform=transform,
            refresh_rate=refresh_rate,
            enabled=enabled,
            description=description,
        )
