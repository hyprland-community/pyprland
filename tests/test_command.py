import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
import sys
from pyprland.command import Pyprland, PyprError


@pytest.fixture
def pyprland_app():
    """Fixture to create a Pyprland instance with mocked dependencies."""
    with patch("pyprland.command.ipc_init"), patch("pyprland.command.get_logger", return_value=Mock()):
        app = Pyprland()
        app.server = AsyncMock()
        app.event_reader = AsyncMock()
        return app


@pytest.mark.asyncio
async def test_load_config_toml(pyprland_app):
    """Test loading a TOML configuration."""
    mock_toml = {"pyprland": {"plugins": ["test_plug"]}}

    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", new_callable=MagicMock),
        patch("tomllib.load", return_value=mock_toml),
        patch("pyprland.ipc.log", new=Mock()),  # Mock the logger used in ipc module
    ):
        # We also need to mock plugin loading to avoid import errors
        # And ensure 'pyprland' key exists in plugins map if we want to avoid KeyError inside load loop
        # But wait, the KeyError 'pyprland' in test failure comes from accessing plugins[name].load_config
        # because the mocked _load_single_plugin doesn't actually put anything in self.plugins for 'pyprland'

        async def mock_load_plugin(name, init):
            # minimal side effect to pretend plugin loaded
            pyprland_app.plugins[name] = Mock()
            pyprland_app.plugins[name].load_config = AsyncMock()
            pyprland_app.plugins[name].on_reload = AsyncMock()
            return True

        with patch.object(pyprland_app, "_load_single_plugin", side_effect=mock_load_plugin) as mock_load:
            await pyprland_app.load_config(init=True)

            assert pyprland_app.config == mock_toml
            # "pyprland" is always loaded first
            # "test_plug" is in the list
            mock_load.assert_any_call("test_plug", True)


@pytest.mark.asyncio
async def test_load_config_toml_with_notify(pyprland_app):
    """Test loading a TOML configuration."""
    mock_toml = {"pyprland": {"plugins": ["test_plug"]}}

    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", new_callable=MagicMock),
        patch("tomllib.load", return_value=mock_toml),
    ):
        pyprland_app.backend.notify_info = AsyncMock()

        # Mock _load_single_plugin to side-effect populate plugins
        async def mock_load_plugin(name, init):
            plug = Mock()
            plug.load_config = AsyncMock()
            plug.on_reload = AsyncMock()
            pyprland_app.plugins[name] = plug
            return True

        with patch.object(pyprland_app, "_load_single_plugin", side_effect=mock_load_plugin):
            await pyprland_app.load_config(init=True)

            assert pyprland_app.config == mock_toml
            assert "test_plug" in pyprland_app.plugins
            assert "pyprland" in pyprland_app.plugins


@pytest.mark.asyncio
async def test_load_config_json_fallback(pyprland_app):
    """Test fallback to JSON if TOML doesn't exist."""
    mock_json = {"pyprland": {"plugins": []}}

    # Sequence of exists checks:
    # 1. __open_config: OLD exists? -> True
    # 2. __open_config: NEW exists? -> False (Triggers warning)
    # 3. __load_config_file: NEW exists? -> False
    # 4. __load_config_file: OLD exists? -> True
    side_effects = [True, False, False, True]

    with (
        patch("os.path.exists", side_effect=side_effects),
        patch("builtins.open", new_callable=MagicMock),
        patch("json.loads", return_value=mock_json),
    ):
        pyprland_app.backend.notify_info = AsyncMock()

        # Mock _load_single_plugin same as above
        async def mock_load_plugin(name, init):
            plug = Mock()
            plug.load_config = AsyncMock()
            pyprland_app.plugins[name] = plug
            return True

        with patch.object(pyprland_app, "_load_single_plugin", side_effect=mock_load_plugin):
            await pyprland_app.load_config(init=False)
            assert pyprland_app.config == mock_json


@pytest.mark.asyncio
async def test_load_config_missing(pyprland_app):
    """Test error raised when no config found."""
    with patch("os.path.exists", return_value=False):
        with pytest.raises(PyprError):
            await pyprland_app.load_config()


@pytest.mark.asyncio
async def test_run_plugin_handler_success(pyprland_app):
    """Test successful execution of a plugin handler."""
    mock_plugin = Mock()
    mock_plugin.name = "test_plugin"
    mock_plugin.test_method = AsyncMock()

    # Mock the log handler since it's called inside _run_plugin_handler
    pyprland_app.log_handler = Mock()

    await pyprland_app._run_plugin_handler(mock_plugin, "test_method", ("arg1",))

    mock_plugin.test_method.assert_called_once_with("arg1")


@pytest.mark.asyncio
async def test_run_plugin_handler_exception(pyprland_app):
    """Test that plugin exceptions are caught and logged."""
    mock_plugin = Mock()
    mock_plugin.name = "test_plugin"
    mock_plugin.test_method = AsyncMock(side_effect=Exception("Boom"))

    pyprland_app.log_handler = Mock()
    pyprland_app.backend.notify_error = AsyncMock()

    # Should not raise
    await pyprland_app._run_plugin_handler(mock_plugin, "test_method", ())

    pyprland_app.backend.notify_error.assert_called()
    pyprland_app.log.exception.assert_called()


@pytest.mark.asyncio
async def test_call_handler_dispatch(pyprland_app):
    """Test dispatching commands to plugins."""
    # Setup two plugins
    p1 = Mock()
    p1.name = "p1"
    p1.aborted = False

    p2 = Mock()
    p2.name = "p2"
    p2.aborted = False
    # Only p2 has the method
    p2.cmd_do_something = AsyncMock()

    pyprland_app.plugins = {"p1": p1, "p2": p2}
    pyprland_app.queues = {"p1": asyncio.Queue(), "p2": asyncio.Queue()}

    # "cmd_" prefix is usually stripped or added depending on context,
    # but _call_handler takes the full name "event_..." or "run_..."
    # The code checks `if hasattr(plugin, full_name)`

    p2.run_mycommand = AsyncMock()

    with patch("pyprland.command.partial") as mock_partial:
        found = await pyprland_app._call_handler("run_mycommand", "arg1")

        assert found is True
        # Verify it was queued for p2
        assert pyprland_app.queues["p2"].qsize() == 1


@pytest.mark.asyncio
async def test_read_command_socket(pyprland_app):
    """Test reading commands from the socket."""
    reader = AsyncMock()
    writer = AsyncMock()
    # writer.write and writer.close are synchronous methods on StreamWriter
    writer.write = Mock()
    writer.close = Mock()

    # Simulate receiving "reload"
    reader.readline.return_value = b"reload\n"

    with patch.object(pyprland_app, "_call_handler", new_callable=AsyncMock) as mock_call:
        await pyprland_app.read_command(reader, writer)

        mock_call.assert_called_with("run_reload", notify="reload")
        writer.write.assert_called()
        writer.close.assert_called()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_read_command_exit(pyprland_app):
    """Test the exit command."""
    reader = AsyncMock()
    writer = AsyncMock()
    # writer.write and writer.close are synchronous methods on StreamWriter
    writer.write = Mock()
    writer.close = Mock()

    reader.readline.return_value = b"exit\n"

    with patch.object(pyprland_app, "_abort_plugins", new_callable=AsyncMock) as mock_abort:
        await pyprland_app.read_command(reader, writer)

        assert pyprland_app.stopped is True
        writer.close.assert_called()
        await writer.wait_closed()
