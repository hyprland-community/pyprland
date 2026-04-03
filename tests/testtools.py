import asyncio
from unittest.mock import AsyncMock, Mock


async def wait_called(fn, timeout=1.0, count=1):
    delay = 0.0
    ival = 0.05
    while True:
        if fn.call_count >= count:
            break
        await asyncio.sleep(ival)
        delay += ival

        if delay > timeout:
            raise TimeoutError()


def get_executed_commands(mock):
    """Flatten all execute() calls into an ordered list of (command, kwargs) tuples.

    Handles both single-string and list-of-strings calls transparently,
    so tests don't break when batching strategy changes.

    Args:
        mock: The AsyncMock used for backend.execute

    Returns:
        A list of ``(command_string, kwargs_dict)`` in call order.
    """
    result = []
    for c in mock.call_args_list:
        args, kwargs = c
        cmd = args[0] if args else None
        if isinstance(cmd, list):
            result.extend((item, kwargs) for item in cmd)
        elif cmd is not None:
            result.append((cmd, kwargs))
    return result


class MockReader:
    """A StreamReader mock."""

    def __init__(self):
        self.q = asyncio.Queue()

    async def readline(self, *a):
        return await self.q.get()

    read = readline


class MockWriter:
    """A StreamWriter mock."""

    def __init__(self):
        self.write = Mock()
        self.drain = AsyncMock()
        self.close = Mock()
        self.wait_closed = AsyncMock()
