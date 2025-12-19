"""Hack to fallback to sync methods if aiofiles is not installed."""

__all__ = ["aiopen", "aiexists", "ailistdir"]

import contextlib
import io
from collections.abc import AsyncIterator

try:
    import aiofiles.os
    from aiofiles import open as aiopen
    from aiofiles.os import listdir as ailistdir

    aiexists = aiofiles.os.path.exists
except ImportError:
    import os

    class AsyncFile:
        """Async file wrapper."""

        def __init__(self, file: io.TextIOWrapper):
            self.file = file

        async def readlines(self) -> list[str]:
            """Async > sync wrapper."""
            return self.file.readlines()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_a):
            self.file.close()

    @contextlib.asynccontextmanager  # type: ignore[no-redef]
    async def aiopen(*args, **kwargs) -> AsyncIterator[AsyncFile]:
        """Async-compatible open function."""
        # use context handler
        with open(*args, **kwargs) as fd:  # noqa: ASYNC101,ASYNC230
            yield AsyncFile(fd)

    async def aiexists(*args, **kwargs) -> bool:
        """Async > sync wrapper."""
        return os.path.exists(*args, **kwargs)

    async def ailistdir(*args, **kwargs) -> list[str]:  # type: ignore[no-redef]
        """Async > sync wrapper."""
        return os.listdir(*args, **kwargs)
