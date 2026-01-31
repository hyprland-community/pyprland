import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pyprland.plugins.wallpapers import Extension
from tests.conftest import make_extension


@pytest.fixture
def extension(mocker, test_logger):
    return make_extension(
        Extension,
        logger=test_logger,
        config={"path": "/tmp/wallpapers", "extensions": ["png", "jpg"], "recurse": False},
        state_variables={},
        hyprctl_json=AsyncMock(return_value=[{"name": "DP-1", "width": 1920, "height": 1080, "transform": 0, "scale": 1.0}]),
        hyprctl=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_on_reload(extension, mocker):
    # Mock expand_path
    mocker.patch("pyprland.plugins.wallpapers.expand_path", side_effect=lambda x: x)

    # Mock get_files_with_ext to return an async iterator (yields full paths like the real function)
    async def mock_get_files(*args, **kwargs):
        yield "/tmp/wallpapers/wp1.png"
        yield "/tmp/wallpapers/wp2.jpg"

    mocker.patch("pyprland.plugins.wallpapers.get_files_with_ext", side_effect=mock_get_files)

    # Mock TaskManager.create to prevent main loop from starting
    # Also mock main_loop to prevent creating an unawaited coroutine
    mocker.patch.object(extension._tasks, "create", return_value=Mock())
    mocker.patch.object(extension, "main_loop", return_value=None)

    await extension.on_reload()

    assert len(extension.image_list) == 2
    assert "/tmp/wallpapers/wp1.png" in extension.image_list
    assert "/tmp/wallpapers/wp2.jpg" in extension.image_list


@pytest.mark.asyncio
async def test_select_next_image(extension):
    extension.image_list = ["/tmp/wallpapers/wp1.png", "/tmp/wallpapers/wp2.jpg"]
    extension.cur_image = "/tmp/wallpapers/wp1.png"

    # Force random.random() to return 1.0 (>= online_ratio of 0.0, so picks local)
    # Force random.choice to pick wp2
    with (
        patch("random.random", return_value=1.0),
        patch("random.choice", return_value="/tmp/wallpapers/wp2.jpg"),
    ):
        next_img = await extension.select_next_image()
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


@pytest.mark.asyncio
async def test_run_palette_terminal(extension, mocker):
    """Test palette command with terminal output."""

    # Mock detect_theme
    async def mock_detect_theme(_):
        return "dark"

    mocker.patch(
        "pyprland.plugins.wallpapers.detect_theme",
        side_effect=mock_detect_theme,
    )

    result = await extension.run_palette("#4285F4")

    assert result is not None
    assert isinstance(result, str)
    # Should contain terminal formatting
    assert "Primary:" in result
    assert "colors.primary" in result
    assert "\033[" in result  # ANSI escape codes


@pytest.mark.asyncio
async def test_run_palette_json(extension, mocker):
    """Test palette command with JSON output."""
    import json

    # Mock detect_theme
    async def mock_detect_theme(_):
        return "dark"

    mocker.patch(
        "pyprland.plugins.wallpapers.detect_theme",
        side_effect=mock_detect_theme,
    )

    result = await extension.run_palette("#FF5500 json")

    assert result is not None
    # Should be valid JSON
    parsed = json.loads(result)
    assert "variables" in parsed
    assert "categories" in parsed
    assert "filters" in parsed


@pytest.mark.asyncio
async def test_run_palette_default_color(extension, mocker):
    """Test palette command with default color when no image is set."""

    # Mock detect_theme
    async def mock_detect_theme(_):
        return "dark"

    mocker.patch(
        "pyprland.plugins.wallpapers.detect_theme",
        side_effect=mock_detect_theme,
    )

    # No current image set
    extension.cur_image = ""

    result = await extension.run_palette("json")

    assert result is not None
    # Should use default Google blue
    import json

    parsed = json.loads(result)
    assert "variables" in parsed


@pytest.mark.asyncio
async def test_run_color(extension, mocker):
    """Test color command generates templates."""
    # Mock _generate_templates
    extension._generate_templates = AsyncMock()

    await extension.run_color("#FF5500")

    extension._generate_templates.assert_called_once_with("color-#FF5500", "#FF5500")


@pytest.mark.asyncio
async def test_run_color_with_scheme(extension, mocker):
    """Test color command with color scheme."""
    # Mock _generate_templates
    extension._generate_templates = AsyncMock()

    await extension.run_color("#FF5500 pastel")

    extension._generate_templates.assert_called_once_with("color-#FF5500", "#FF5500")
    assert extension.config["color_scheme"] == "pastel"
