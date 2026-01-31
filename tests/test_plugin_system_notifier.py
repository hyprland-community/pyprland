import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pyprland.plugins.system_notifier import Extension, builtin_parsers
from tests.conftest import make_extension


@pytest_asyncio.fixture
async def extension():
    ext = make_extension(
        Extension,
        config={"parsers": {}, "sources": [], "default_color": "#000000"},
    )
    yield ext
    await ext.exit()


@pytest.mark.asyncio
async def test_initialization(extension):
    assert extension._tasks.running is False  # TaskManager starts stopped
    assert extension.sources == {}
    assert extension.parsers == {}


@pytest.mark.asyncio
async def test_on_reload_builtin_parser(extension):
    # Should load builtin parsers
    await extension.on_reload()
    assert "journal" in extension.parsers
    assert extension._tasks.running  # TaskManager should be running after reload


@pytest.mark.asyncio
async def test_on_reload_custom_parser(extension):
    extension.config["parsers"] = {"custom": [{"pattern": "test", "color": "#123456"}]}
    await extension.on_reload()
    assert "custom" in extension.parsers
    assert "journal" in extension.parsers  # built-in should still be there


@pytest.mark.asyncio
async def test_parser_matching(extension):
    # Setup a queue for a custom parser
    q = asyncio.Queue()
    extension.parsers["test_parser"] = q
    extension.config["default_color"] = "#FFFFFF"

    # Start TaskManager so the parser loop runs
    extension._tasks.start()

    # Define parser properties
    props = [{"pattern": r"Error: (.*)", "filter": r"s/Error: (.*)/Something failed: \1/", "color": "#FF0000", "duration": 5}]

    with patch("pyprland.plugins.system_notifier.convert_color", side_effect=lambda x: int(x[1:], 16) if x.startswith("#") else x):
        task = asyncio.create_task(extension.start_parser("test_parser", props))
        await asyncio.sleep(0.01)
        await q.put("Error: Database connection lost")
        await asyncio.sleep(0.01)

        extension.backend.notify.assert_called_with("Something failed: Database connection lost", color=0xFF0000, duration=5)

    # Feed non-matching content
    extension.backend.notify.reset_mock()
    await q.put("Info: All systems go")
    await asyncio.sleep(0.01)
    extension.backend.notify.assert_not_called()

    # Clean up
    await extension._tasks.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_notify_send_option(extension):
    extension.config["use_notify_send"] = True
    q = asyncio.Queue()
    extension.parsers["test_parser"] = q

    # Start TaskManager so the parser loop runs
    extension._tasks.start()

    props = [{"pattern": r"Match me", "duration": 2}]

    with patch("pyprland.plugins.system_notifier.notify_send", new_callable=AsyncMock) as mock_notify_send:
        task = asyncio.create_task(extension.start_parser("test_parser", props))
        await asyncio.sleep(0.01)

        await q.put("Match me")
        await asyncio.sleep(0.01)

        # Should use notify_send instead of self.backend.notify
        extension.backend.notify.assert_not_called()

        mock_notify_send.assert_called_once()
        args, kwargs = mock_notify_send.call_args
        assert args[0] == "Match me"
        assert kwargs["duration"] == 2000

        await extension._tasks.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_exit_cleanup(extension):
    # Start the TaskManager and add some sources
    extension._tasks.start()

    mock_proc = Mock()
    mock_proc.stop = AsyncMock()
    extension.sources["cmd"] = mock_proc

    await extension.exit()

    assert extension._tasks.running is False
    mock_proc.stop.assert_called_once()
    assert extension.sources == {}
