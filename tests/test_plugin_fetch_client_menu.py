import pytest
from unittest.mock import Mock, AsyncMock, patch
from pyprland.plugins.fetch_client_menu import Extension
from pyprland.common import state


@pytest.fixture
def extension():
    state.active_workspace = "1"
    state.active_window = "0x123"

    ext = Extension("fetch_client_menu")
    ext.hyprctl = AsyncMock()
    ext.notify_error = AsyncMock()
    ext.get_clients = AsyncMock()
    ext.menu = AsyncMock()
    ext.config = {"separator": "|"}
    ext._windows_origins = {}

    # Mock ensure_menu_configured to prevent it from overwriting our mock menu
    ext.ensure_menu_configured = AsyncMock()

    return ext


@pytest.mark.asyncio
async def test_run_unfetch_client_success(extension):
    extension._windows_origins = {"0x123": "2"}

    await extension.run_unfetch_client()

    extension.hyprctl.assert_called_with("movetoworkspacesilent 2,address:0x123")


@pytest.mark.asyncio
async def test_run_unfetch_client_unknown(extension):
    extension._windows_origins = {}

    await extension.run_unfetch_client()

    extension.notify_error.assert_called_with("unknown window origin")
    extension.hyprctl.assert_not_called()


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
    # Should move window
    extension.hyprctl.assert_called_with(f"movetoworkspace {state.active_workspace},address:0xDEF")


@pytest.mark.asyncio
async def test_run_fetch_client_menu_cancel(extension):
    extension.get_clients.return_value = []
    extension.menu.run.return_value = None  # User cancelled

    await extension.run_fetch_client_menu()

    extension.hyprctl.assert_not_called()
