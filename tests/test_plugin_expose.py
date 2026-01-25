import pytest
from unittest.mock import Mock, AsyncMock
from pyprland.plugins.expose import Extension
from pyprland.models import ClientInfo
from pyprland.common import SharedState


@pytest.fixture
def sample_clients():
    return [
        {"address": "0x1", "workspace": {"id": 1, "name": "1"}, "class": "App1"},
        {"address": "0x2", "workspace": {"id": 2, "name": "2"}, "class": "App2"},
        {"address": "0x3", "workspace": {"id": -99, "name": "special:scratch"}, "class": "SpecialApp"},
    ]


@pytest.fixture
def extension():
    ext = Extension("expose")
    ext.backend = AsyncMock()
    ext.hyprctl = ext.backend.execute
    ext.get_clients = AsyncMock()
    ext.state = SharedState()
    # Note: expose.py uses self.get_config_bool() which goes through Plugin.get_config()
    # We mock the plugin method, not config.get_bool
    ext.get_config_bool = Mock(return_value=False)  # Default include_special=False
    return ext


@pytest.mark.asyncio
async def test_exposed_clients_filtering(extension, sample_clients):
    extension.exposed = sample_clients

    # Test default: include_special=False (should exclude ID <= 0)
    filtered = extension.exposed_clients
    assert len(filtered) == 2
    assert all(c["workspace"]["id"] > 0 for c in filtered)

    # Test include_special=True
    extension.get_config_bool.return_value = True
    all_clients = extension.exposed_clients
    assert len(all_clients) == 3


@pytest.mark.asyncio
async def test_run_expose_enable(extension, sample_clients):
    # Setup
    extension.exposed = []
    # Mock returning only normal clients for simplicity
    normal_clients = sample_clients[:2]
    extension.get_clients.return_value = normal_clients

    extension.state.active_workspace = "1"

    await extension.run_expose()

    # Verify state was captured
    assert extension.exposed == normal_clients

    # Verify commands
    calls = extension.hyprctl.call_args[0][0]
    # Should have 2 moves + 1 toggle
    assert len(calls) == 3
    assert "movetoworkspacesilent special:exposed,address:0x1" in calls
    assert "movetoworkspacesilent special:exposed,address:0x2" in calls
    assert "togglespecialworkspace exposed" in calls


@pytest.mark.asyncio
async def test_run_expose_disable(extension, sample_clients):
    # Setup
    normal_clients = sample_clients[:2]
    extension.exposed = normal_clients

    extension.state.active_window = "0x1"

    await extension.run_expose()

    # Verify state was cleared
    assert extension.exposed == []

    # Verify commands
    calls = extension.hyprctl.call_args[0][0]
    # Should have 2 moves (restore) + 1 toggle + 1 focus
    assert len(calls) == 4
    # Check restoration to original workspaces
    assert "movetoworkspacesilent 1,address:0x1" in calls
    assert "movetoworkspacesilent 2,address:0x2" in calls
    assert "togglespecialworkspace exposed" in calls
    assert "focuswindow address:0x1" in calls


@pytest.mark.asyncio
async def test_run_expose_empty_workspace(extension):
    # Setup
    extension.exposed = []
    extension.get_clients.return_value = []

    extension.state.active_workspace = "1"

    await extension.run_expose()

    # Exposed should be empty
    assert extension.exposed == []

    # Verify commands - likely just the toggle if logic persists
    calls = extension.hyprctl.call_args[0][0]
    assert len(calls) == 1
    assert calls[0] == "togglespecialworkspace exposed"
