import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from pyprland.plugins.wallpapers.imageutils import (
    expand_path,
    get_files_with_ext,
    MonitorInfo,
    RoundedImageManager,
    to_hex,
    to_rgb,
    to_rgba,
    get_variant_color,
    IMAGE_FORMAT,
)


def test_expand_path():
    with patch.dict(os.environ, {"MY_VAR": "expanded"}):
        path = "$MY_VAR/path"
        expanded = expand_path(path)
        assert "expanded/path" in expanded

    # ~ expansion is harder to test reliably across environments without mocking expanduser specifically,
    # but expand_path calls os.path.expanduser.
    with patch("os.path.expanduser") as mock_expanduser:
        mock_expanduser.return_value = "/home/user/path"
        assert expand_path("~/path") == "/home/user/path"


@pytest.mark.asyncio
async def test_get_files_with_ext():
    # We need to mock ailistdir (from pyprland.aioops) and os.path
    with (
        patch("pyprland.plugins.wallpapers.imageutils.ailistdir") as mock_ailistdir,
        patch("os.path.isdir") as mock_isdir,
        patch("os.path.join", side_effect=os.path.join),
    ):
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

        def isdir_side_effect(path):
            return path.endswith("sub")

        mock_isdir.side_effect = isdir_side_effect

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


def test_rounded_image_manager_paths():
    manager = RoundedImageManager(radius=10)
    monitor = MonitorInfo(name="DP-1", width=1920, height=1080, transform=0, scale=1.0)

    key = manager._build_key(monitor, "/path/to/img.jpg")
    assert key == "0:1.0x1920x1080:/path/to/img.jpg"

    path = manager.get_path(key)
    assert str(manager.tmpdir) in path
    assert path.endswith(f".{IMAGE_FORMAT}")


def test_rounded_image_manager_processing():
    with (
        patch("pyprland.plugins.wallpapers.imageutils.Image") as MockImage,
        patch("pyprland.plugins.wallpapers.imageutils.ImageOps") as MockImageOps,
        patch("pyprland.plugins.wallpapers.imageutils.ImageDraw") as MockImageDraw,
        patch("os.path.exists", return_value=False),
        patch("builtins.open", Mock()),
    ):  # Prevent accidental file access? No, Image.open handles files.
        manager = RoundedImageManager(radius=10)
        monitor = MonitorInfo(name="DP-1", width=100, height=100, transform=0, scale=1.0)

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
