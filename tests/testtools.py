import asyncio
from unittest.mock import AsyncMock, Mock


async def wait_called(fn, timeout=1.0):
    delay = 0.0
    while True:
        if fn.call_count:
            break
        await asyncio.sleep(0.02)
        delay += 0.02

        if delay > timeout:
            raise TimeoutError()


class MockReader:
    "A StreamReader mock"

    def __init__(self):
        self.q = asyncio.Queue()

    async def readline(self, *a):
        return await self.q.get()

    read = readline


class MockWriter:
    "A StreamWriter mock"

    def __init__(self):
        self.write = Mock()
        self.drain = AsyncMock()
        self.close = Mock()
        self.wait_closed = AsyncMock()
