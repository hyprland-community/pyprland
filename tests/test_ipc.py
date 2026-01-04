import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pyprland import ipc
from pyprland.types import PyprError


@pytest.fixture
def mock_open_connection(mocker):
    reader = AsyncMock()
    # StreamWriter methods write and close are synchronous, drain and wait_closed are async
    writer = Mock()
    writer.drain = AsyncMock()
    writer.wait_closed = AsyncMock()

    mock_connect = mocker.patch("asyncio.open_unix_connection", return_value=(reader, writer))
    return mock_connect, reader, writer


@pytest.mark.asyncio
async def test_hyprctl_connection_context_manager(mock_open_connection):
    mock_connect, reader, writer = mock_open_connection
    logger = Mock()

    async with ipc.hyprctl_connection(logger) as (r, w):
        assert r == reader
        assert w == writer

    writer.close.assert_called_once()
    writer.wait_closed.assert_awaited_once()


@pytest.mark.asyncio
async def test_hyprctl_connection_error(mocker):
    mocker.patch("asyncio.open_unix_connection", side_effect=FileNotFoundError)
    logger = Mock()

    with pytest.raises(PyprError):
        async with ipc.hyprctl_connection(logger):
            pass

    logger.critical.assert_called_with("hyprctl socket not found! is it running ?")


@pytest.mark.asyncio
async def test_get_response(mock_open_connection):
    mock_connect, reader, writer = mock_open_connection
    logger = Mock()
    reader.read.return_value = b'{"status": "ok"}'

    result = await ipc._get_response(b"command", logger)

    assert result == {"status": "ok"}
    writer.write.assert_called_with(b"command")
    writer.drain.assert_awaited_once()


@pytest.mark.asyncio
async def test_hyprctl_success(mock_open_connection):
    mock_connect, reader, writer = mock_open_connection
    logger = Mock()
    reader.read.return_value = b"ok"

    result = await ipc.hyprctl("some_command", logger=logger)

    assert result is True
    writer.write.assert_called_with(b"/dispatch some_command")


@pytest.mark.asyncio
async def test_hyprctl_failure(mock_open_connection):
    mock_connect, reader, writer = mock_open_connection
    logger = Mock()
    reader.read.return_value = b"err"

    result = await ipc.hyprctl("some_command", logger=logger)

    assert result is False
    logger.error.assert_called()


@pytest.mark.asyncio
async def test_hyprctl_batch(mock_open_connection):
    mock_connect, reader, writer = mock_open_connection
    logger = Mock()
    reader.read.return_value = b"okok"

    cmds = ["cmd1", "cmd2"]
    result = await ipc.hyprctl(cmds, logger=logger)

    assert result is True
    # Verify the batch format string
    call_args = writer.write.call_args[0][0]
    assert b"[[BATCH]]" in call_args
    assert b"dispatch cmd1" in call_args
    assert b"dispatch cmd2" in call_args


@pytest.mark.asyncio
async def test_get_client_props(mock_open_connection):
    # Mock hyprctl_json to avoid socket usage
    with patch("pyprland.ipc.hyprctl_json", new_callable=AsyncMock) as mock_json:
        clients = [{"address": "0x123", "class": "Term"}, {"address": "0x456", "class": "Browser"}]
        mock_json.return_value = clients
        logger = Mock()

        # By address
        client = await ipc.get_client_props(logger, addr="0x123")
        assert client == clients[0]

        # By class
        client = await ipc.get_client_props(logger, cls="Browser")
        assert client == clients[1]

        # By custom prop
        client = await ipc.get_client_props(logger, title="Something")  # Not found
        assert client is None
