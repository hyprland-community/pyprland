"""Hack to fallback to sync methods if aiofiles is not installed."""

__all__ = ["aiopen", "aiexists", "ailistdir"]

import contextlib
import io

try:
    import aiofiles.os
    from aiofiles import open as aiopen
    from aiofiles.os import listdir as ailistdir

    aiexists = aiofiles.os.path.exists
except ImportError:
    import os

    class AsyncFile:
        def __init__(self, file: io.TextIOWrapper):
            self.file = file

        async def readlines(self) -> list[str]:
            return self.file.readlines()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self.file.close()

    @contextlib.asynccontextmanager
    async def aiopen(*args, **kwargs) -> AsyncFile:
        yield AsyncFile(open(*args, **kwargs))

    async def aiexists(*args, **kwargs) -> bool:
        """Async > sync wrapper."""
        return os.path.exists(*args, **kwargs)

    async def ailistdir(*args, **kwargs) -> list[str]:
        """Async > sync wrapper."""
        return os.listdir(*args, **kwargs)
