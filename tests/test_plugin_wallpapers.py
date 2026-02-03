import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from pyprland.plugins.wallpapers import Extension, OnlineState
from pyprland.plugins.wallpapers.models import Theme
from pyprland.plugins.wallpapers.online import OnlineFetcher
from tests.conftest import make_extension


@pytest.fixture
def extension(mocker, test_logger):
    ext = make_extension(
        Extension,
        logger=test_logger,
        config={"path": "/tmp/wallpapers", "extensions": ["png", "jpg"], "recurse": False},
    )
    # Configure backend methods with specific return values
    ext.backend.execute_json.return_value = [{"name": "DP-1", "width": 1920, "height": 1080, "transform": 0, "scale": 1.0}]
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

    # Mock TaskManager.create to prevent main loop from starting
    # Use a simple lambda to avoid MagicMock introspection issues with coroutines
    extension._tasks.create = Mock(return_value=Mock())
    extension._loop_started = True  # Prevent the create call entirely

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

    await extension.run_wall_next()

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
    assert theme == Theme.DARK


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
        return Theme.DARK

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
        return Theme.DARK

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
        return Theme.DARK

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


# --- Prefetch Tests ---


@pytest.fixture
def online_extension(mocker, test_logger):
    """Extension with online fetching enabled."""
    ext = make_extension(
        Extension,
        logger=test_logger,
        config={"path": "/tmp/wallpapers", "extensions": ["png", "jpg"], "online_ratio": 0.5},
    )
    # Configure backend methods with specific return values
    ext.backend.execute_json.return_value = [{"name": "DP-1", "width": 1920, "height": 1080, "transform": 0, "scale": 1.0}]
    # Initialize image_list
    ext.image_list = []
    # Set up mock online state
    mock_fetcher = AsyncMock(spec=OnlineFetcher)
    mock_fetcher.get_image = AsyncMock(return_value=Path("/tmp/wallpapers/online/test.jpg"))
    ext._online = OnlineState(
        fetcher=mock_fetcher,
        folder_path=Path("/tmp/wallpapers/online"),
        cache=Mock(),
        rounded_cache=Mock(),
        prefetched_path=None,
    )
    return ext


@pytest.mark.asyncio
async def test_fetch_online_image_uses_prefetched(online_extension, mocker):
    """_fetch_online_image() uses prefetched path if available."""
    # Set prefetched path
    online_extension._online.prefetched_path = "/tmp/wallpapers/online/prefetched.jpg"

    # Mock aiexists to return True (file exists)
    mocker.patch("pyprland.plugins.wallpapers.aiexists", return_value=True)

    result = await online_extension._fetch_online_image()

    assert result == "/tmp/wallpapers/online/prefetched.jpg"
    # Prefetched path should be cleared after use
    assert online_extension._online.prefetched_path is None
    # Fetcher should NOT be called since we used prefetched
    online_extension._online.fetcher.get_image.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_online_image_prefetched_missing(online_extension, mocker):
    """_fetch_online_image() falls back to fetcher if prefetched file is gone."""
    # Set prefetched path
    online_extension._online.prefetched_path = "/tmp/wallpapers/online/deleted.jpg"

    # Mock aiexists to return False (file was deleted)
    mocker.patch("pyprland.plugins.wallpapers.aiexists", return_value=False)

    # Mock fetch_monitors
    mocker.patch(
        "pyprland.plugins.wallpapers.fetch_monitors",
        return_value=[Mock(width=1920, height=1080, transform=0)],
    )

    result = await online_extension._fetch_online_image()

    # Should have called fetcher since prefetched file was missing
    online_extension._online.fetcher.get_image.assert_called_once()
    assert result == str(Path("/tmp/wallpapers/online/test.jpg"))


@pytest.mark.asyncio
async def test_prefetch_online_image_success(online_extension, mocker):
    """_prefetch_online_image() downloads and stores path in OnlineState."""
    # Mock fetch_monitors
    mocker.patch(
        "pyprland.plugins.wallpapers.fetch_monitors",
        return_value=[Mock(width=1920, height=1080, transform=0)],
    )

    # Ensure no prefetched path initially
    assert online_extension._online.prefetched_path is None

    await online_extension._prefetch_online_image()

    # Path should be stored
    assert online_extension._online.prefetched_path == "/tmp/wallpapers/online/test.jpg"
    # Should be added to image_list
    assert "/tmp/wallpapers/online/test.jpg" in online_extension.image_list


@pytest.mark.asyncio
async def test_prefetch_online_image_retry(online_extension, mocker):
    """_prefetch_online_image() retries on failure with exponential backoff."""
    # Mock fetch_monitors
    mocker.patch(
        "pyprland.plugins.wallpapers.fetch_monitors",
        return_value=[Mock(width=1920, height=1080, transform=0)],
    )

    # Mock fetcher to fail twice then succeed
    online_extension._online.fetcher.get_image = AsyncMock(
        side_effect=[
            Exception("Network error"),
            Exception("Timeout"),
            Path("/tmp/wallpapers/online/retry_success.jpg"),
        ]
    )

    # Mock asyncio.sleep to track delays
    sleep_calls = []

    async def mock_sleep(delay):
        sleep_calls.append(delay)
        # Don't actually sleep in tests

    mocker.patch("asyncio.sleep", side_effect=mock_sleep)

    await online_extension._prefetch_online_image()

    # Should have retried with exponential backoff (2s, 4s)
    assert len(sleep_calls) == 2
    assert sleep_calls[0] == 2  # First retry: 2 seconds
    assert sleep_calls[1] == 4  # Second retry: 4 seconds

    # Should have succeeded on third attempt
    assert online_extension._online.prefetched_path == "/tmp/wallpapers/online/retry_success.jpg"
