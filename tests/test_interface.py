import pytest
from unittest.mock import Mock, AsyncMock, patch
from pyprland.plugins.interface import Plugin
from pyprland.common import Configuration


class ConcretePlugin(Plugin):
    """A concrete implementation of Plugin for testing."""

    pass


@pytest.fixture
def plugin():
    # Mocking get_controls to avoid importing ipc module which might try to connect or setup logging
    with patch("pyprland.plugins.interface.get_controls") as mock_get_controls:
        # Mock what get_controls returns (tuple of callables)
        mock_get_controls.return_value = (Mock(), Mock(), Mock(), Mock(), Mock())
        plugin = ConcretePlugin("test_plugin")
        # Manually attach mocks for methods used in get_clients
        plugin.hyprctl_json = AsyncMock()
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
    plugin.hyprctl_json.return_value = clients_data

    # 1. Default: mapped=True, no workspace filter
    clients = await plugin.get_clients()
    assert len(clients) == 3
    assert "0x2" not in [c["address"] for c in clients]

    # 2. mapped=False (should return all?)
    # Re-read implementation: if (not mapped or client["mapped"])
    # So if mapped=False, it returns everything (True or True is True)
    clients = await plugin.get_clients(mapped=False)
    assert len(clients) == 4

    # 3. Filter by workspace
    clients = await plugin.get_clients(workspace="2")
    # Should get mapped clients on workspace 2
    assert len(clients) == 1
    assert clients[0]["address"] == "0x3"

    # 4. Filter by workspace blacklist
    clients = await plugin.get_clients(workspace_bl="1")
    # Should get mapped clients NOT on workspace 1
    # 0x1 is on ws 1. 0x2 is unmapped. 0x3 on ws 2. 0x4 on ws 3.
    # Should get 0x3 and 0x4
    assert len(clients) == 2
    addresses = [c["address"] for c in clients]
    assert "0x3" in addresses
    assert "0x4" in addresses
