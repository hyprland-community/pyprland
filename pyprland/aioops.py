"""Hack to fallback to sync methods if aiofiles is not installed."""

__all__ = ["aiopen", "aiexists", "ailistdir"]

import io

try:
    from aiofiles import open as aiopen
    from aiofiles.os import listdir as ailistdir
    from aiofiles.path import exists as aiexists
except ImportError:
    import os

    async def aioopen(*args, **kwargs) -> io.TextIOWrapper:
        """Async > sync wrapper."""
        f = open(*args, **kwargs)  # noqa
        _orig_readlines = f.readlines

        async def _new_readlines(*args, **kwargs) -> list[str]:
            return _orig_readlines(*args, **kwargs)

        f.readlines = _new_readlines
        return f

    async def aiexists(*args, **kwargs) -> bool:
        """Async > sync wrapper."""
        return os.path.exists(*args, **kwargs)

    async def ailistdir(*args, **kwargs) -> list[str]:
        """Async > sync wrapper."""
        return os.listdir(*args, **kwargs)
