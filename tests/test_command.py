import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
import sys
import os
import tempfile
from pathlib import Path
from pyprland.command import Pyprland
from pyprland.models import ExitCode, PyprError
from pyprland.validate_cli import run_validate, _load_plugin_module


@pytest.fixture
def pyprland_app():
    """Fixture to create a Pyprland instance with mocked dependencies."""
    with patch("pyprland.manager.get_logger", return_value=Mock()):
        app = Pyprland()
        app.server = AsyncMock()
        app.event_reader = AsyncMock()
        app.log_handler = Mock()  # Required for _run_plugin_handler
        return app


@pytest.mark.asyncio
async def test_load_config_toml(pyprland_app):
    """Test loading a TOML configuration."""
    mock_toml = {"pyprland": {"plugins": ["test_plug"]}}

    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", new_callable=MagicMock),
        patch("tomllib.load", return_value=mock_toml),
        patch("pyprland.ipc._state.log", new=Mock()),  # Mock the logger used in ipc module
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
            pyprland_app.plugins[name].validate_config = Mock(return_value=[])
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
            plug.validate_config = Mock(return_value=[])
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
        patch.object(Path, "exists", side_effect=side_effects),
        patch.object(Path, "open", new_callable=MagicMock),
        patch("json.loads", return_value=mock_json),
    ):
        pyprland_app.backend.notify_info = AsyncMock()

        # Mock _load_single_plugin same as above
        async def mock_load_plugin(name, init):
            plug = Mock()
            plug.load_config = AsyncMock()
            plug.validate_config = Mock(return_value=[])
            pyprland_app.plugins[name] = plug
            return True

        with patch.object(pyprland_app, "_load_single_plugin", side_effect=mock_load_plugin):
            await pyprland_app.load_config(init=False)
            assert pyprland_app.config == mock_json


@pytest.mark.asyncio
async def test_load_config_missing(pyprland_app):
    """Test error raised when no config found."""
    with patch.object(Path, "exists", return_value=False):
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
async def test_run_plugin_handler_exception(pyprland_app, monkeypatch):
    """Test that plugin exceptions are caught and logged."""
    # Disable strict mode for this test - we're testing the resilient behavior
    monkeypatch.delenv("PYPRLAND_STRICT_ERRORS", raising=False)

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

    with patch("pyprland.manager.partial") as mock_partial:
        handled, success, msg = await pyprland_app._call_handler("run_mycommand", "arg1")

        assert handled is True
        assert success is True
        assert msg == ""
        # Verify it was queued for p2
        assert pyprland_app.queues["p2"].qsize() == 1


@pytest.mark.asyncio
async def test_call_handler_dispatch_with_wait(pyprland_app):
    """Test dispatching commands to plugins with wait=True."""
    p1 = Mock()
    p1.name = "p1"
    p1.aborted = False

    pyprland_app.plugins = {"p1": p1}
    pyprland_app.queues = {"p1": asyncio.Queue()}
    pyprland_app.log_handler = Mock()
    pyprland_app.pyprland_mutex_event = asyncio.Event()
    pyprland_app.pyprland_mutex_event.set()
    pyprland_app.stopped = False

    p1.run_mycommand = AsyncMock()

    # Start a background task to process the queue (simulates _plugin_runner_loop)
    async def queue_processor():
        q = pyprland_app.queues["p1"]
        while True:
            task = await q.get()
            if task is None:
                break
            await task()

    processor_task = asyncio.create_task(queue_processor())

    try:
        handled, success, msg = await pyprland_app._call_handler("run_mycommand", "arg1", wait=True)

        assert handled is True
        assert success is True
        assert msg == ""
        p1.run_mycommand.assert_called_once_with("arg1")
    finally:
        # Stop the processor
        await pyprland_app.queues["p1"].put(None)
        await processor_task


@pytest.mark.asyncio
async def test_call_handler_unknown_command(pyprland_app):
    """Test handling unknown command."""
    pyprland_app.plugins = {}
    pyprland_app.backend.notify_info = AsyncMock()

    handled, success, msg = await pyprland_app._call_handler("run_nonexistent", notify="nonexistent")

    assert handled is False
    assert success is False
    assert "Unknown command" in msg
    pyprland_app.backend.notify_info.assert_called()


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
        # Mock returns (handled=True, success=True, msg="")
        mock_call.return_value = (True, True, "")
        await pyprland_app.read_command(reader, writer)

        mock_call.assert_called_with("run_reload", notify="reload", wait=True)
        writer.write.assert_called()
        writer.close.assert_called()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_read_command_socket_error(pyprland_app):
    """Test reading commands from the socket with error response."""
    reader = AsyncMock()
    writer = AsyncMock()
    writer.write = Mock()
    writer.close = Mock()

    reader.readline.return_value = b"failing_command\n"

    with patch.object(pyprland_app, "_call_handler", new_callable=AsyncMock) as mock_call:
        # Mock returns (handled=True, success=False, msg="error message")
        mock_call.return_value = (True, False, "test_plugin::run_failing: Exception occurred")
        await pyprland_app.read_command(reader, writer)

        # Verify ERROR response was sent
        calls = writer.write.call_args_list
        assert any(b"ERROR:" in call[0][0] for call in calls)
        writer.close.assert_called()


@pytest.mark.asyncio
async def test_read_command_socket_unknown(pyprland_app):
    """Test reading unknown command from the socket."""
    reader = AsyncMock()
    writer = AsyncMock()
    writer.write = Mock()
    writer.close = Mock()

    reader.readline.return_value = b"unknown_cmd\n"

    with patch.object(pyprland_app, "_call_handler", new_callable=AsyncMock) as mock_call:
        # Mock returns (handled=False, success=False, msg="Unknown command")
        mock_call.return_value = (False, False, 'Unknown command "unknown_cmd". Try "help" for available commands.')
        await pyprland_app.read_command(reader, writer)

        # Verify ERROR response was sent
        calls = writer.write.call_args_list
        assert any(b"ERROR:" in call[0][0] for call in calls)
        writer.close.assert_called()


@pytest.mark.asyncio
async def test_read_command_exit(pyprland_app):
    """Test the exit command."""
    reader = AsyncMock()
    writer = AsyncMock()
    # writer.write and writer.close are synchronous methods on StreamWriter
    writer.write = Mock()
    writer.close = Mock()

    reader.readline.return_value = b"exit\n"

    # Set up the pyprland plugin with manager reference so run_exit works
    from pyprland.plugins.pyprland import Extension

    pyprland_plugin = Extension("pyprland")
    pyprland_plugin.manager = pyprland_app
    pyprland_app.plugins["pyprland"] = pyprland_plugin

    with patch.object(pyprland_app, "_abort_plugins", new_callable=AsyncMock) as mock_abort:
        await pyprland_app.read_command(reader, writer)

        assert pyprland_app.stopped is True
        # exit command now writes OK response before triggering abort
        writer.write.assert_called()
        await writer.wait_closed()


def test_load_plugin_module_builtin():
    """Test loading a built-in plugin module."""
    extension_class = _load_plugin_module("magnify")
    assert extension_class is not None
    assert hasattr(extension_class, "config_schema")


def test_load_plugin_module_not_found():
    """Test loading a non-existent plugin module."""
    extension_class = _load_plugin_module("nonexistent_plugin_xyz")
    assert extension_class is None


def test_run_validate_valid_config():
    """Test validate command with a valid config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = os.path.join(tmpdir, ".config", "hypr")
        os.makedirs(config_dir)
        config_file = os.path.join(config_dir, "pyprland.toml")

        # Write a valid config
        with open(config_file, "w") as f:
            f.write("""
[pyprland]
plugins = ["magnify"]

[magnify]
factor = 2.5
duration = 10
""")

        with patch.dict(os.environ, {"HOME": tmpdir}):
            with pytest.raises(SystemExit) as exc_info:
                run_validate()
            assert exc_info.value.code == ExitCode.SUCCESS


def test_run_validate_missing_required_field():
    """Test validate command with missing required field."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = os.path.join(tmpdir, ".config", "hypr")
        os.makedirs(config_dir)
        config_file = os.path.join(config_dir, "pyprland.toml")

        # Write a config with missing required "path" field for wallpapers
        with open(config_file, "w") as f:
            f.write("""
[pyprland]
plugins = ["wallpapers"]

[wallpapers]
interval = 10
""")

        with patch.dict(os.environ, {"HOME": tmpdir}):
            with pytest.raises(SystemExit) as exc_info:
                run_validate()
            # Should fail with USAGE_ERROR due to missing required field
            assert exc_info.value.code == ExitCode.USAGE_ERROR


def test_run_validate_config_not_found():
    """Test validate command when config file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"HOME": tmpdir}):
            with pytest.raises(SystemExit) as exc_info:
                run_validate()
            assert exc_info.value.code == ExitCode.ENV_ERROR
