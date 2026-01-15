import pytest
from unittest.mock import Mock, AsyncMock, patch
from pyprland.plugins.interface import Plugin
from pyprland.common import Configuration


class ConcretePlugin(Plugin):
    """A concrete implementation of Plugin for testing."""

    pass


@pytest.fixture
def plugin():
    plugin = ConcretePlugin("test_plugin")
    # Manually attach mocks for methods used in get_clients
    plugin.hyprctl_json = AsyncMock()
    plugin.state = Mock()
    plugin.state.environment = "hyprland"

    # Mock the backend
    plugin.backend = Mock()
    plugin.backend.get_clients = AsyncMock()
    plugin.backend.execute = AsyncMock()
    plugin.backend.execute_json = AsyncMock()

    return plugin


@pytest.mark.asyncio
async def test_plugin_init(plugin):
    assert plugin.name == "test_plugin"
    assert isinstance(plugin.config, Configuration)
    # Ensure init methods exist and are callable (even if empty)
    await plugin.init()
    await plugin.on_reload()
    await plugin.exit()


@pytest.mark.asyncio
async def test_load_config(plugin):
    config = {"test_plugin": {"option1": "value1", "option2": 123}, "other_plugin": {"ignore": "me"}}

    await plugin.load_config(config)

    assert plugin.config["option1"] == "value1"
    assert plugin.config["option2"] == 123
    assert "ignore" not in plugin.config


@pytest.mark.asyncio
async def test_get_clients_filter(plugin):
    clients_data = [
        {"mapped": True, "workspace": {"name": "1"}, "address": "0x1"},
        {"mapped": False, "workspace": {"name": "2"}, "address": "0x2"},
        {"mapped": True, "workspace": {"name": "2"}, "address": "0x3"},
        {"mapped": True, "workspace": {"name": "3"}, "address": "0x4"},
    ]

    # Simulate backend behavior since we are testing the interface delegation,
    # but strictly speaking if the logic moved to backend, this test should test backend or integration.
    # However, to fix the test and verify delegation:

    async def mock_backend_get_clients(mapped=True, workspace=None, workspace_bl=None):
        # Replicate old logic for the sake of verifying the plugin method calls backend correctly
        # Or simpler: verify backend is called with correct args.
        # But verify result requires mocking the return.

        # Let's filter manually here to mimic what backend should do
        filtered = []
        for client in clients_data:
            if mapped and not client["mapped"]:
                continue
            if workspace and client["workspace"]["name"] != workspace:
                continue
            if workspace_bl and client["workspace"]["name"] == workspace_bl:
                continue
            filtered.append(client)
        return filtered

    plugin.backend.get_clients.side_effect = mock_backend_get_clients

    # 1. Default: mapped=True, no workspace filter
    clients = await plugin.get_clients()
    plugin.backend.get_clients.assert_called_with(True, None, None)
    assert len(clients) == 3
    assert "0x2" not in [c["address"] for c in clients]

    # 2. mapped=False (should return all?)
    clients = await plugin.get_clients(mapped=False)
    plugin.backend.get_clients.assert_called_with(False, None, None)
    assert len(clients) == 4

    # 3. Filter by workspace
    clients = await plugin.get_clients(workspace="2")
    plugin.backend.get_clients.assert_called_with(True, "2", None)
    assert len(clients) == 1
    assert clients[0]["address"] == "0x3"

    # 4. Filter by workspace blacklist
    clients = await plugin.get_clients(workspace_bl="1")
    plugin.backend.get_clients.assert_called_with(True, None, "1")
    assert len(clients) == 2
    addresses = [c["address"] for c in clients]
    assert "0x3" in addresses
    assert "0x4" in addresses
