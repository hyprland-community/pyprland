import pytest
import os
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pyprland.plugins.wallpapers import Extension
from pyprland.config import Configuration
from pyprland.common import SharedState


@pytest.fixture
def extension(mocker, test_logger):
    # Mock global state variables that might be accessed

    ext = Extension("wallpapers")
    ext.state = SharedState()
    ext.state.variables = {}
    ext.config = Configuration({"path": "/tmp/wallpapers", "extensions": ["png", "jpg"], "recurse": False}, logger=test_logger)
    ext.log = Mock()
    ext.hyprctl_json = AsyncMock(return_value=[{"name": "DP-1", "width": 1920, "height": 1080, "transform": 0, "scale": 1.0}])
    ext.hyprctl = AsyncMock()
    return ext


@pytest.mark.asyncio
async def test_on_reload(extension, mocker):
    # Mock expand_path
    mocker.patch("pyprland.plugins.wallpapers.expand_path", side_effect=lambda x: x)

    # Mock get_files_with_ext to return an async iterator (yields full paths like the real function)
    async def mock_get_files(*args, **kwargs):
        yield "/tmp/wallpapers/wp1.png"
        yield "/tmp/wallpapers/wp2.jpg"

    mocker.patch("pyprland.plugins.wallpapers.get_files_with_ext", side_effect=mock_get_files)

    # Mock create_task to prevent main loop from running
    mocker.patch("asyncio.create_task")
    # Mock main_loop to avoid creating an orphaned coroutine
    mocker.patch.object(extension, "main_loop", new_callable=Mock)

    await extension.on_reload()

    assert len(extension.image_list) == 2
    assert "/tmp/wallpapers/wp1.png" in extension.image_list
    assert "/tmp/wallpapers/wp2.jpg" in extension.image_list


@pytest.mark.asyncio
async def test_select_next_image(extension):
    extension.image_list = ["/tmp/wallpapers/wp1.png", "/tmp/wallpapers/wp2.jpg"]
    extension.cur_image = "/tmp/wallpapers/wp1.png"

    # Force random to pick wp2
    with patch("random.choice", return_value="/tmp/wallpapers/wp2.jpg"):
        next_img = extension.select_next_image()
        assert next_img == "/tmp/wallpapers/wp2.jpg"
        assert extension.cur_image == "/tmp/wallpapers/wp2.jpg"


@pytest.mark.asyncio
async def test_run_wall_next(extension):
    extension.next_background_event = asyncio.Event()
    extension._paused = True

    await extension.run_wall("next")

    assert extension._paused is False
    assert extension.next_background_event.is_set()


@pytest.mark.asyncio
async def test_detect_theme(mocker, test_logger):
    # Mock subprocess for gsettings
    proc_mock = AsyncMock()
    proc_mock.communicate.return_value = (b"'prefer-dark'\n", b"")
    proc_mock.returncode = 0

    mocker.patch("asyncio.create_subprocess_shell", return_value=proc_mock)

    from pyprland.plugins.wallpapers.theme import detect_theme

    theme = await detect_theme(test_logger)
    assert theme == "dark"


@pytest.mark.asyncio
async def test_material_palette_generation():
    # Just verify that it generates keys correctly based on the constant dictionary
    rgb_list = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]  # Red, Green, Blue

    # Mock nicify_oklab and get_variant_color to avoid complex color math dependencies in test if not needed
    # But since we imported them in the module, let's assume they work or mock them if they are external
    # For now, let's test if the structure is correct

    with (
        patch("pyprland.plugins.wallpapers.colorutils.nicify_oklab", side_effect=lambda rgb, **kwargs: rgb),
        patch("pyprland.plugins.wallpapers.theme.get_variant_color", return_value=(100, 100, 100)),
    ):
        # Simple process_color mock
        def process_color(rgb):
            return (0.0, 0.5, 0.5)  # hue, light, sat

        from pyprland.plugins.wallpapers.theme import generate_palette

        palette = generate_palette(rgb_list, process_color)

        assert "colors.primary.dark" in palette
        assert "colors.secondary.light" in palette
        assert "colors.surface.default.hex" in palette
