"""Image utilities for the wallpapers plugin."""

import colorsys
import os
import os.path
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from ..aioops import ailistdir
from .wallpapers_utils import Image, ImageDraw, ImageOps

IMAGE_FORMAT = "jpg"


def expand_path(path: str) -> str:
    """Expand the path."""
    return os.path.expanduser(os.path.expandvars(path))


async def get_files_with_ext(path: str, extensions: list[str], recurse: bool = True) -> AsyncIterator[str]:
    """Return files matching `extension` in given `path`. Can optionally `recurse` subfolders.."""
    for fname in await ailistdir(path):
        ext = fname.rsplit(".", 1)[-1]
        full_path = os.path.join(path, fname)
        if ext.lower() in extensions:
            yield full_path
        elif recurse and os.path.isdir(full_path):
            async for v in get_files_with_ext(full_path, extensions, True):
                yield v


@dataclass(slots=True)
class MonitorInfo:
    """Monitor information."""

    name: str
    width: int
    height: int
    transform: int
    scale: float


class RoundedImageManager:
    """Manages rounded and scaled images for monitors."""

    def __init__(self, radius: int) -> None:
        """Initialize the manager."""
        self.radius = radius

        self.tmpdir = Path("~").expanduser() / ".cache" / "pyprland" / "wallpapers"
        self.tmpdir.mkdir(parents=True, exist_ok=True)

    def _build_key(self, monitor: MonitorInfo, image_path: str) -> str:
        return f"{monitor.transform}:{monitor.scale}x{monitor.width}x{monitor.height}:{image_path}"

    def get_path(self, key: str) -> str:
        """Get the path for a given key."""
        return os.path.join(self.tmpdir, f"{abs(hash((key, self.radius)))}.{IMAGE_FORMAT}")

    def scale_and_round(self, src: str, monitor: MonitorInfo) -> str:
        """Scale and round the image for the given monitor."""
        key = self._build_key(monitor, src)
        dest = self.get_path(key)
        if not os.path.exists(dest):
            with Image.open(src) as img:
                is_rotated = monitor.transform % 2
                width, height = (monitor.width, monitor.height) if not is_rotated else (monitor.height, monitor.width)
                width = int(width / monitor.scale)
                height = int(height / monitor.scale)
                resample = Image.Resampling.LANCZOS
                resized = ImageOps.fit(img, (width, height), method=resample)

                scale = 4
                image_width, image_height = resized.width * scale, resized.height * scale
                rounded_mask = Image.new("L", (image_width, image_height), 0)  # type: ignore
                corner_draw = ImageDraw.Draw(rounded_mask)  # type: ignore
                corner_draw.rounded_rectangle((0, 0, image_width - 1, image_height - 1), radius=self.radius * scale, fill=255)
                mask = rounded_mask.resize(resized.size, resample=resample)

                result = Image.new("RGB", resized.size, "black")  # type: ignore
                result.paste(resized.convert("RGB"), mask=mask)
                result.convert("RGB").save(dest)

        return dest


def to_hex(r: float, g: float, b: float) -> str:
    """Convert float rgb to hex."""
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def to_rgb(r: float, g: float, b: float) -> str:
    """Convert float rgb to rgb string."""
    return f"rgb({int(r * 255)}, {int(g * 255)}, {int(b * 255)})"


def to_rgba(r: float, g: float, b: float) -> str:
    """Convert float rgb to rgba string."""
    return f"rgba({int(r * 255)}, {int(g * 255)}, {int(b * 255)}, 1.0)"


def get_variant_color(h: float, s: float, l: float) -> tuple[float, float, float]:  # noqa: E741
    """Get variant color."""
    return colorsys.hls_to_rgb(h, max(0.0, min(1.0, l)), s)
