import pytest
from unittest.mock import AsyncMock
from pyprland.plugins.fetch_client_menu import Extension
from tests.conftest import make_extension


@pytest.fixture
def extension():
    return make_extension(
        Extension,
        config={"separator": "|"},
        menu=AsyncMock(),
        _windows_origins={},
        ensure_menu_configured=AsyncMock(),
    )


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
