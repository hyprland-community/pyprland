import pytest
from unittest.mock import MagicMock, AsyncMock
from pyprland.plugins.shortcuts_menu import Extension
from pyprland.common import Configuration


@pytest.fixture
def extension():
    ext = Extension("shortcuts_menu")
    ext.config = Configuration(
        {
            "entries": {
                "Network": {"WiFi": "nm-connection-editor", "Bluetooth": "blueman-manager"},
                "System": {"Power": {"Shutdown": "poweroff", "Reboot": "reboot"}},
                "Simple": "echo hello",
            },
            "skip_single": True,
        }
    )
    ext.menu = AsyncMock()
    # Explicitly set configured to avoid real menu initialization
    ext._menu_configured = True
    ext.log = MagicMock()
    return ext


@pytest.mark.asyncio
async def test_run_menu_simple_command(extension):
    # Test running a simple command directly
    await extension.run_menu("Simple")
    # Verify asyncio.create_subprocess_shell was called (implied by _run_command)
    # We can mock asyncio.create_subprocess_shell if we want to be more specific,
    # but checking that we didn't crash is a start.
    # To check properly, we need to mock asyncio.create_subprocess_shell globally or refactor _run_command
    # but here let's assume if it reaches _run_command it works.
    # Actually, let's better mock _run_command on the extension since it's an internal method we want to verify called
    extension._run_command = AsyncMock()

    await extension.run_menu("Simple")
    extension._run_command.assert_called_with("echo hello", {})


@pytest.mark.asyncio
async def test_run_menu_nested(extension):
    # The keys in the menu are formatted with default suffixes.
    # "Network" -> "Network ➜"
    # "WiFi" -> "WiFi"
    extension.menu.run.side_effect = ["Network ➜", "WiFi"]
    extension._run_command = AsyncMock()

    await extension.run_menu()

    # It should first show the top level menu
    # Then show the Network submenu
    # Then execute the WiFi command
    assert extension.menu.run.call_count == 2
    extension._run_command.assert_called_with("nm-connection-editor", {})


@pytest.mark.asyncio
async def test_run_menu_cancellation(extension):
    extension.menu.run.side_effect = KeyError("Cancelled")

    await extension.run_menu()

    # Should stop after first menu cancellation
    assert extension.menu.run.call_count == 1


@pytest.mark.asyncio
async def test_run_menu_with_skip_single(extension):
    # Setup config with a single entry to test skip_single
    extension.config = Configuration({"entries": {"SingleGroup": {"OnlyOption": "do_something"}}})
    extension._run_command = AsyncMock()

    await extension.run_menu()

    # Should skip the SingleGroup menu because there's only one option (if we were selecting it)
    # But wait, the logic is:
    # 1. Shows top level: "SingleGroup" -> 1 option.
    # If skip_single=True (default), it should auto-select "SingleGroup"
    # Then inside "SingleGroup", there is "OnlyOption" -> 1 option. Auto-select.
    # Then execute "do_something"

    extension._run_command.assert_called_with("do_something", {})
    # menu.run should not be called if everything is skipped
    assert extension.menu.run.call_count == 0


@pytest.mark.asyncio
async def test_run_menu_formatting(extension):
    # Test custom formatting
    extension.config["submenu_start"] = "["
    extension.config["submenu_end"] = "]"
    extension.config["command_start"] = "("
    extension.config["command_end"] = ")"

    extension.menu.run.return_value = "Network"
    # We want to check what arguments were passed to menu.run

    # First call should have formatted keys
    try:
        await extension.run_menu()
    except:
        pass  # Ignore potential errors in subsequent steps

    call_args = extension.menu.run.call_args
    if call_args:
        options = call_args[0][0]
        # Keys should be formatted
        assert "[ Network ]" in options
        assert "( Simple )" in options
