import pytest
from unittest.mock import AsyncMock
from pyprland.plugins.fetch_client_menu import Extension
from tests.conftest import make_extension


@pytest.fixture
def extension():
    ext = make_extension(
        Extension,
        config={"separator": "|", "center_on_fetch": True, "margin": 60},
        menu=AsyncMock(),
        _windows_origins={},
        ensure_menu_configured=AsyncMock(),
    )
    # Mock monitor and client props for centering
    ext.get_focused_monitor_or_warn = AsyncMock(return_value={"x": 0, "y": 0, "width": 1920, "height": 1080, "scale": 1.0, "transform": 0})
    ext.backend.get_client_props = AsyncMock(return_value={"address": "0xDEF", "size": [800, 600], "floating": False})
    return ext


@pytest.mark.asyncio
async def test_run_unfetch_client_success(extension):
    extension._windows_origins = {"0x123": "2"}

    await extension.run_unfetch_client()

    extension.backend.move_window_to_workspace.assert_called_with("0x123", "2")


@pytest.mark.asyncio
async def test_run_unfetch_client_unknown(extension):
    extension._windows_origins = {}

    await extension.run_unfetch_client()

    extension.backend.notify_error.assert_called_with("unknown window origin")
    extension.backend.execute.assert_not_called()


@pytest.mark.asyncio
async def test_run_fetch_client_menu(extension):
    clients = [
        {"address": "0xABC", "title": "Window 1", "workspace": {"name": "2"}},
        {"address": "0xDEF", "title": "Window 2", "workspace": {"name": "3"}},
    ]
    extension.get_clients.return_value = clients
    extension.menu.run.return_value = "2 | Window 2"  # User selects second item

    await extension.run_fetch_client_menu()

    # Check menu call options
    extension.menu.run.assert_called()
    options = extension.menu.run.call_args[0][0]
    assert "1 | Window 1" in options
    assert "2 | Window 2" in options

    # Verify action
    # Should save origin
    assert extension._windows_origins["0xDEF"] == "3"
    # Should move window (non-silent since we want to follow the window)
    extension.backend.move_window_to_workspace.assert_called_with("0xDEF", extension.state.active_workspace, silent=False)


@pytest.mark.asyncio
async def test_run_fetch_client_menu_cancel(extension):
    extension.get_clients.return_value = []
    extension.menu.run.return_value = None  # User cancelled

    await extension.run_fetch_client_menu()

    extension.backend.move_window_to_workspace.assert_not_called()


@pytest.mark.asyncio
async def test_center_window_on_monitor_floats_and_centers(extension):
    """Test that fetching a window floats it and centers on monitor."""
    clients = [
        {"address": "0xABC", "title": "Window 1", "workspace": {"name": "2"}},
    ]
    extension.get_clients.return_value = clients
    extension.menu.run.return_value = "1 | Window 1"
    extension.backend.get_client_props = AsyncMock(return_value={"address": "0xABC", "size": [800, 600], "floating": False})

    await extension.run_fetch_client_menu()

    # Should toggle floating since window is not floating
    extension.backend.toggle_floating.assert_called_with("0xABC")
    # Should move to centered position: (1920-800)/2=560, (1080-600)/2=240
    extension.backend.move_window.assert_called_with("0xABC", 560, 240)


@pytest.mark.asyncio
async def test_center_window_already_floating(extension):
    """Test that already floating windows don't get toggle_floating called."""
    clients = [
        {"address": "0xABC", "title": "Window 1", "workspace": {"name": "2"}},
    ]
    extension.get_clients.return_value = clients
    extension.menu.run.return_value = "1 | Window 1"
    extension.backend.get_client_props = AsyncMock(return_value={"address": "0xABC", "size": [800, 600], "floating": True})

    await extension.run_fetch_client_menu()

    # Should NOT toggle floating since window is already floating
    extension.backend.toggle_floating.assert_not_called()
    # Should still center
    extension.backend.move_window.assert_called_with("0xABC", 560, 240)


@pytest.mark.asyncio
async def test_center_window_resizes_if_too_large(extension):
    """Test that large windows are resized to fit within margin."""
    clients = [
        {"address": "0xABC", "title": "Window 1", "workspace": {"name": "2"}},
    ]
    extension.get_clients.return_value = clients
    extension.menu.run.return_value = "1 | Window 1"
    # Window larger than monitor - 2*margin (1920-120=1800, 1080-120=960)
    extension.backend.get_client_props = AsyncMock(return_value={"address": "0xABC", "size": [2000, 1200], "floating": True})

    await extension.run_fetch_client_menu()

    # Should resize to available space: 1920-120=1800, 1080-120=960
    extension.backend.resize_window.assert_called_with("0xABC", 1800, 960)
    # Then center with new size: (1920-1800)/2=60, (1080-960)/2=60
    extension.backend.move_window.assert_called_with("0xABC", 60, 60)


@pytest.mark.asyncio
async def test_center_window_with_rotated_monitor(extension):
    """Test that rotated monitors swap width/height."""
    clients = [
        {"address": "0xABC", "title": "Window 1", "workspace": {"name": "2"}},
    ]
    extension.get_clients.return_value = clients
    extension.menu.run.return_value = "1 | Window 1"
    # Rotated monitor (transform=1 = 90 degrees)
    extension.get_focused_monitor_or_warn = AsyncMock(
        return_value={"x": 0, "y": 0, "width": 1920, "height": 1080, "scale": 1.0, "transform": 1}
    )
    extension.backend.get_client_props = AsyncMock(return_value={"address": "0xABC", "size": [400, 600], "floating": True})

    await extension.run_fetch_client_menu()

    # Rotated: effective dimensions are 1080x1920
    # Center: (1080-400)/2=340, (1920-600)/2=660
    extension.backend.move_window.assert_called_with("0xABC", 340, 660)


@pytest.mark.asyncio
async def test_center_window_disabled(extension):
    """Test that centering can be disabled via config."""
    clients = [
        {"address": "0xABC", "title": "Window 1", "workspace": {"name": "2"}},
    ]
    extension.get_clients.return_value = clients
    extension.menu.run.return_value = "1 | Window 1"
    extension.config["center_on_fetch"] = False

    await extension.run_fetch_client_menu()

    # Should not call any centering-related methods
    extension.backend.toggle_floating.assert_not_called()
    extension.backend.move_window.assert_not_called()
    extension.backend.resize_window.assert_not_called()


@pytest.mark.asyncio
async def test_center_window_with_scaled_monitor(extension):
    """Test centering with scaled monitor (e.g., HiDPI)."""
    clients = [
        {"address": "0xABC", "title": "Window 1", "workspace": {"name": "2"}},
    ]
    extension.get_clients.return_value = clients
    extension.menu.run.return_value = "1 | Window 1"
    # 2x scaled monitor
    extension.get_focused_monitor_or_warn = AsyncMock(
        return_value={"x": 0, "y": 0, "width": 3840, "height": 2160, "scale": 2.0, "transform": 0}
    )
    extension.backend.get_client_props = AsyncMock(return_value={"address": "0xABC", "size": [800, 600], "floating": True})

    await extension.run_fetch_client_menu()

    # Scaled: effective dimensions are 1920x1080
    # Center: (1920-800)/2=560, (1080-600)/2=240
    extension.backend.move_window.assert_called_with("0xABC", 560, 240)
