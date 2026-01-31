"""Image utilities for the wallpapers plugin."""

import colorsys
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from ...aioops import ailistdir
from .cache import ImageCache
from .colorutils import Image, ImageDraw, ImageOps

IMAGE_FORMAT = "jpg"


def expand_path(path: str) -> str:
    """Expand the path.

    Args:
        path: The path to expand (handles ~ and environment variables)
    """
    return str(Path(os.path.expandvars(path)).expanduser())


async def get_files_with_ext(path: str, extensions: list[str], recurse: bool = True) -> AsyncIterator[str]:
    """Return files matching `extension` in given `path`. Can optionally `recurse` subfolders..

    Args:
        path: Directory to search in
        extensions: List of file extensions to include
        recurse: Whether to search recursively in subdirectories
    """
    for fname in await ailistdir(path):
        ext = fname.rsplit(".", 1)[-1]
        full_path = f"{path}/{fname}"
        if ext.lower() in extensions:
            yield full_path
        elif recurse and Path(full_path).is_dir():
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

    def __init__(self, radius: int, cache: ImageCache) -> None:
        """Initialize the manager.

        Args:
            radius: Corner radius for rounding
            cache: ImageCache instance for caching rounded images
        """
        self.radius = radius
        self.cache = cache

    def _build_key(self, monitor: MonitorInfo, image_path: str) -> str:
        """Build the cache key for the image.

        Args:
            monitor: Monitor information
            image_path: Path to the source image

        Returns:
            A unique cache key including radius, monitor info, and image path.
        """
        return f"rounded:{self.radius}:{monitor.transform}:{monitor.scale}x{monitor.width}x{monitor.height}:{image_path}"

    def scale_and_round(self, src: str, monitor: MonitorInfo) -> str:
        """Scale and round the image for the given monitor.

        Args:
            src: Source image path
            monitor: Monitor information

        Returns:
            Path to the cached rounded image.
        """
        key = self._build_key(monitor, src)

        # Check cache for valid entry
        cached = self.cache.get(key, IMAGE_FORMAT)
        if cached:
            return str(cached)

        # Get path for new cache entry
        dest = self.cache.get_path(key, IMAGE_FORMAT)

        with Image.open(src) as img:
            is_rotated = monitor.transform % 2
            width, height = (monitor.width, monitor.height) if not is_rotated else (monitor.height, monitor.width)
            width = int(width / monitor.scale)
            height = int(height / monitor.scale)
            resample = Image.Resampling.LANCZOS
            resized = ImageOps.fit(img, (width, height), method=resample)

            scale = 4
            mask = self._create_rounded_mask(resized.width, resized.height, scale, resample)

            result = Image.new("RGB", resized.size, "black")
            result.paste(resized.convert("RGB"), mask=mask)
            result.convert("RGB").save(str(dest))

        return str(dest)

    def _create_rounded_mask(self, width: int, height: int, scale: int, resample: Image.Resampling) -> Image.Image:
        """Create a rounded mask.

        Args:
            width: Target width
            height: Target height
            scale: Scaling factor for quality
            resample: Resampling method
        """
        image_width, image_height = width * scale, height * scale
        rounded_mask = Image.new("L", (image_width, image_height), 0)
        corner_draw = ImageDraw.Draw(rounded_mask)
        corner_draw.rounded_rectangle((0, 0, image_width - 1, image_height - 1), radius=self.radius * scale, fill=255)
        return rounded_mask.resize((width, height), resample=resample)


def to_hex(red: int, green: int, blue: int) -> str:
    """Convert integer rgb to hex.

    Args:
        red: Red component (0-255)
        green: Green component (0-255)
        blue: Blue component (0-255)
    """
    return f"#{red:02x}{green:02x}{blue:02x}"


def to_rgb(red: int, green: int, blue: int) -> str:
    """Convert integer rgb to rgb string.

    Args:
        red: Red component (0-255)
        green: Green component (0-255)
        blue: Blue component (0-255)
    """
    return f"rgb({red}, {green}, {blue})"


def to_rgba(red: int, green: int, blue: int) -> str:
    """Convert integer rgb to rgba string.

    Args:
        red: Red component (0-255)
        green: Green component (0-255)
        blue: Blue component (0-255)
    """
    return f"rgba({red}, {green}, {blue}, 1.0)"


def get_variant_color(hue: float, saturation: float, lightness: float) -> tuple[int, int, int]:
    """Get variant color.

    Args:
        hue: Hue value (0.0-1.0)
        saturation: Saturation value (0.0-1.0)
        lightness: Lightness value (0.0-1.0)
    """
    r, g, b = colorsys.hls_to_rgb(hue, max(0.0, min(1.0, lightness)), saturation)
    return int(r * 255), int(g * 255), int(b * 255)
