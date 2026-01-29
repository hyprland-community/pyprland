"""Hack to fallback to sync methods if aiofiles is not installed."""

__all__ = ["aiopen", "aiexists", "ailistdir", "DebouncedTask"]

import asyncio
import contextlib
import io
from collections.abc import AsyncIterator, Callable, Coroutine
from types import TracebackType
from typing import Any, Self

try:
    import aiofiles.os
    from aiofiles import open as aiopen
    from aiofiles.os import listdir as ailistdir

    aiexists = aiofiles.os.path.exists
except ImportError:
    import os

    class AsyncFile:
        """Async file wrapper.

        Args:
            file: The file object to wrap
        """

        def __init__(self, file: io.TextIOWrapper) -> None:
            self.file = file

        async def readlines(self) -> list[str]:
            """Read lines."""
            return self.file.readlines()

        async def read(self) -> str:
            """Read lines."""
            return self.file.read()

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
        ) -> None:
            self.file.close()

    @contextlib.asynccontextmanager  # type: ignore[no-redef, unused-ignore]
    async def aiopen(*args, **kwargs) -> AsyncIterator[AsyncFile]:
        """Async > sync wrapper."""
        with open(*args, **kwargs) as f:  # noqa: ASYNC230, pylint: disable=unspecified-encoding
            yield AsyncFile(f)

    async def aiexists(*args, **kwargs) -> bool:
        """Async > sync wrapper."""
        return os.path.exists(*args, **kwargs)

    async def ailistdir(*args, **kwargs) -> list[str]:  # type: ignore[no-redef, unused-ignore]
        """Async > sync wrapper."""
        return os.listdir(*args, **kwargs)


class DebouncedTask:
    """A debounced async task with ignore window support.

    Useful for plugins that react to events they can also trigger themselves.
    The ignore window prevents reacting to self-triggered events.

    Usage:
        # Create instance (typically in on_reload)
        self._relayout_debouncer = DebouncedTask(ignore_window=3.0)

        # In event handler - schedule with delay
        self._relayout_debouncer.schedule(self._delayed_relayout, delay=1.0)

        # Before self-triggering actions - set ignore window
        self._relayout_debouncer.set_ignore_window()
        await self.backend.execute(cmd, base_command="keyword")
    """

    def __init__(self, ignore_window: float = 3.0) -> None:
        """Initialize the debounced task.

        Args:
            ignore_window: Duration in seconds to ignore schedule() calls
                          after set_ignore_window() is called.
        """
        self._task: asyncio.Task[None] | None = None
        self._ignore_window = ignore_window
        self._ignore_until: float = 0

    def schedule(self, coro_func: Callable[[], Coroutine[Any, Any, Any]], delay: float = 0) -> bool:
        """Schedule or reschedule the task.

        Cancels any pending task before scheduling. If within the ignore window,
        the task is not scheduled.

        Args:
            coro_func: Async function to call (no arguments)
            delay: Delay in seconds before executing

        Returns:
            True if scheduled, False if in ignore window
        """
        if asyncio.get_event_loop().time() < self._ignore_until:
            return False

        self.cancel()

        async def _run() -> None:
            try:
                if delay > 0:
                    await asyncio.sleep(delay)
                await coro_func()
            except asyncio.CancelledError:
                pass

        self._task = asyncio.create_task(_run())
        return True

    def set_ignore_window(self) -> None:
        """Start the ignore window and cancel any pending task.

        Calls to schedule() will be ignored until the window expires.
        """
        self._ignore_until = asyncio.get_event_loop().time() + self._ignore_window
        self.cancel()

    def cancel(self) -> None:
        """Cancel any pending task."""
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None
