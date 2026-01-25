"""X11/Xorg backend using xrandr for monitor detection."""

import asyncio
import re
from logging import Logger

from ..models import MonitorInfo
from .fallback import FallbackBackend, make_monitor_info

# Map xrandr rotation names to transform integers
# 0=normal, 1=90° (left), 2=180° (inverted), 3=270° (right)
TRANSFORM_MAP = {
    "normal": 0,
    "left": 1,
    "inverted": 2,
    "right": 3,
}


class XorgBackend(FallbackBackend):
    """X11/Xorg backend using xrandr for monitor information.

    Provides monitor detection for the wallpapers plugin on X11 systems.
    Does not support window management, events, or other compositor features.
    """

    @classmethod
    async def is_available(cls) -> bool:
        """Check if xrandr is available.

        Returns:
            True if xrandr command works
        """
        return await cls._check_command("xrandr --version")

    async def get_monitors(self, *, log: Logger, include_disabled: bool = False) -> list[MonitorInfo]:
        """Get monitor information from xrandr.

        Args:
            log: Logger to use for this operation
            include_disabled: If True, include disconnected monitors

        Returns:
            List of MonitorInfo dicts
        """
        try:
            proc = await asyncio.create_subprocess_shell(
                "xrandr --query",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                log.error("xrandr failed: %s", stderr.decode())
                return []

            return self._parse_xrandr_output(stdout.decode(), include_disabled, log)

        except OSError as e:
            log.warning("Failed to get monitors from xrandr: %s", e)
            return []

    def _parse_xrandr_output(  # pylint: disable=too-many-locals
        self, output: str, include_disabled: bool, log: Logger
    ) -> list[MonitorInfo]:
        """Parse xrandr --query output to extract monitor information.

        Example xrandr output:
            DP-1 connected primary 1920x1080+0+0 left (normal left inverted right x axis y axis) 527mm x 296mm
               1920x1080     60.00*+
            HDMI-1 connected 2560x1440+1920+0 (normal left inverted right x axis y axis) 597mm x 336mm
               2560x1440     59.95*+
            VGA-1 disconnected (normal left inverted right x axis y axis)

        Args:
            output: Raw xrandr output
            include_disabled: Whether to include disconnected outputs
            log: Logger for debug output

        Returns:
            List of MonitorInfo dicts
        """
        monitors: list[MonitorInfo] = []

        # Pattern to match connected outputs with resolution
        # Groups: name, primary?, resolution+position, transform?
        # Example: "DP-1 connected primary 1920x1080+0+0 left"
        pattern = re.compile(
            r"^(\S+)\s+(connected|disconnected)"  # name, status
            r"(?:\s+primary)?"  # optional primary
            r"(?:\s+(\d+)x(\d+)\+(\d+)\+(\d+))?"  # optional WxH+X+Y
            r"(?:\s+(normal|left|inverted|right))?"  # optional transform
        )

        for line in output.splitlines():
            match = pattern.match(line)
            if not match:
                continue

            name = match.group(1)
            connected = match.group(2) == "connected"
            width = int(match.group(3)) if match.group(3) else 0
            height = int(match.group(4)) if match.group(4) else 0
            x = int(match.group(5)) if match.group(5) else 0
            y = int(match.group(6)) if match.group(6) else 0
            transform_str = match.group(7) or "normal"

            # Skip disconnected unless requested
            if not connected and not include_disabled:
                continue

            # Skip outputs without resolution (not active)
            if (width == 0 or height == 0) and not include_disabled:
                continue

            transform = TRANSFORM_MAP.get(transform_str, 0)

            log.debug("xrandr monitor: %s %dx%d+%d+%d transform=%d", name, width, height, x, y, transform)

            # Build MonitorInfo - X11 doesn't have fractional scaling via xrandr
            monitor = make_monitor_info(
                index=len(monitors),
                name=name,
                width=width,
                height=height,
                pos_x=x,
                pos_y=y,
                transform=transform,
                enabled=connected,
            )
            monitors.append(monitor)

        return monitors
