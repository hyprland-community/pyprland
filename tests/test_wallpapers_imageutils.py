import os
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pyprland.plugins.wallpapers.cache import ImageCache
from pyprland.plugins.wallpapers.imageutils import (
    IMAGE_FORMAT,
    MonitorInfo,
    RoundedImageManager,
    expand_path,
    get_effective_dimensions,
    get_files_with_ext,
    get_variant_color,
    to_hex,
    to_rgb,
    to_rgba,
)


def test_expand_path():
    with patch.dict(os.environ, {"MY_VAR": "expanded"}):
        path = "$MY_VAR/path"
        expanded = expand_path(path)
        assert "expanded/path" in expanded

    # ~ expansion - expand_path calls Path.expanduser()
    with patch.object(Path, "expanduser") as mock_expanduser:
        mock_expanduser.return_value = Path("/home/user/path")
        assert expand_path("~/path") == "/home/user/path"


@pytest.mark.asyncio
async def test_get_files_with_ext():
    # We need to mock ailistdir (from pyprland.aioops) and Path.is_dir
    with patch("pyprland.plugins.wallpapers.imageutils.ailistdir") as mock_ailistdir:
        # Structure:
        # /root
        #   - a.jpg
        #   - b.png (skipped)
        #   - sub/
        #     - c.jpg

        async def ailistdir_side_effect(path):
            if path == "/root":
                return ["a.jpg", "b.png", "sub"]
            if path == "/root/sub":
                return ["c.jpg"]
            return []

        mock_ailistdir.side_effect = ailistdir_side_effect

        # Mock Path.is_dir() to return True for paths ending with "sub"
        original_is_dir = Path.is_dir

        def mock_is_dir(self):
            return str(self).endswith("sub")

        with patch.object(Path, "is_dir", mock_is_dir):
            # Test non-recursive
            files = []
            async for f in get_files_with_ext("/root", ["jpg"], recurse=False):
                files.append(f)
            assert len(files) == 1
            assert files[0].endswith("a.jpg")

            # Test recursive
            files = []
            async for f in get_files_with_ext("/root", ["jpg"], recurse=True):
                files.append(f)
            assert len(files) == 2
            assert any(f.endswith("a.jpg") for f in files)
            assert any(f.endswith("c.jpg") for f in files)


def test_color_conversions():
    assert to_hex(255, 0, 0) == "#ff0000"
    assert to_hex(0, 255, 0) == "#00ff00"
    assert to_hex(0, 0, 255) == "#0000ff"

    assert to_rgb(255, 0, 0) == "rgb(255, 0, 0)"
    assert to_rgba(255, 0, 0) == "rgba(255, 0, 0, 1.0)"


def test_get_variant_color():
    # HLS: Hue, Lightness, Saturation
    # Hue=0 (Red), L=0.5, S=1.0 -> RGB(255, 0, 0)
    r, g, b = get_variant_color(0.0, 1.0, 0.5)
    assert r == 255
    assert g == 0
    assert b == 0

    # Check clamping logic (max(0, min(1.0, lightness)))
    # If we pass lightness > 1.0, it should clamp to 1.0 (White)
    r, g, b = get_variant_color(0.0, 1.0, 1.5)
    assert r == 255
    assert g == 255
    assert b == 255


def test_rounded_image_manager_paths(tmp_path):
    cache = ImageCache(cache_dir=tmp_path)
    manager = RoundedImageManager(radius=10, cache=cache)
    monitor = MonitorInfo(name="DP-1", width=1920, height=1080, transform=0, scale=1.0)

    key = manager._build_key(monitor, "/path/to/img.jpg")
    # Key now includes radius prefix
    assert key == "rounded:10:0:1.0x1920x1080:/path/to/img.jpg"

    # Path is obtained through cache.get_path()
    path = cache.get_path(key, IMAGE_FORMAT)
    assert str(tmp_path) in str(path)
    assert str(path).endswith(f".{IMAGE_FORMAT}")


def test_get_effective_dimensions_no_rotation():
    """Transforms 0, 2, 4, 6 should NOT swap dimensions."""
    for transform in [0, 2, 4, 6]:
        monitor = MonitorInfo(name="DP-1", width=1920, height=1080, transform=transform, scale=1.0)
        w, h = get_effective_dimensions(monitor)
        assert (w, h) == (1920, 1080), f"Transform {transform} should not swap dimensions"


def test_get_effective_dimensions_rotated():
    """Transforms 1, 3, 5, 7 (90/270 degree rotations) should swap width and height."""
    for transform in [1, 3, 5, 7]:
        monitor = MonitorInfo(name="DP-1", width=1920, height=1080, transform=transform, scale=1.0)
        w, h = get_effective_dimensions(monitor)
        assert (w, h) == (1080, 1920), f"Transform {transform} should swap dimensions"


def test_rounded_image_manager_processing(tmp_path):
    with (
        patch("pyprland.plugins.wallpapers.imageutils.Image") as MockImage,
        patch("pyprland.plugins.wallpapers.imageutils.ImageOps") as MockImageOps,
        patch("pyprland.plugins.wallpapers.imageutils.ImageDraw") as MockImageDraw,
        patch.object(Path, "exists", return_value=False),
        patch("builtins.open", Mock()),
    ):  # Prevent accidental file access? No, Image.open handles files.
        cache = ImageCache(cache_dir=tmp_path)
        manager = RoundedImageManager(radius=10, cache=cache)
        monitor = MonitorInfo(name="DP-1", width=100, height=100, transform=0, scale=1.0)

        # Mock cache.get() to return None (cache miss)
        cache.get = Mock(return_value=None)

        mock_img = Mock()
        mock_img.width = 200
        mock_img.height = 200
        MockImage.open.return_value.__enter__.return_value = mock_img

        # Mock resize/fit result
        mock_resized = Mock()
        mock_resized.size = (100, 100)
        mock_resized.width = 100
        mock_resized.height = 100
        MockImageOps.fit.return_value = mock_resized

        # Mock new image creation
        mock_new_img = Mock()
        MockImage.new.return_value = mock_new_img

        dest = manager.scale_and_round("/path/to/img.jpg", monitor)

        # Verify workflow
        MockImage.open.assert_called_with("/path/to/img.jpg")
        # Check fit called with correct dimensions (width/scale, height/scale)
        MockImageOps.fit.assert_called()

        # Check mask creation called
        MockImageDraw.Draw.assert_called()

        # Check saving
        mock_new_img.convert.return_value.save.assert_called_with(dest)
