"""Async operation utilities.

Provides fallback sync methods if aiofiles is not installed,
plus async task management utilities.
"""

__all__ = ["DebouncedTask", "TaskManager", "aiexists", "ailistdir", "aiopen", "aioremove", "airmdir", "airmtree", "graceful_cancel_tasks"]

import asyncio
import contextlib
import io
import os
import shutil
from collections.abc import AsyncIterator, Callable, Coroutine
from types import TracebackType
from typing import Any, Self

try:
    import aiofiles.os
    from aiofiles import open as aiopen
    from aiofiles.os import listdir as ailistdir

    aiexists = aiofiles.os.path.exists
except ImportError:

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
        with open(*args, **kwargs) as f:  # noqa: ASYNC230, PTH123  # pylint: disable=unspecified-encoding
            yield AsyncFile(f)

    async def aiexists(*args, **kwargs) -> bool:
        """Async > sync wrapper."""
        return os.path.exists(*args, **kwargs)

    async def ailistdir(*args, **kwargs) -> list[str]:  # type: ignore[no-redef, unused-ignore]
        """Async > sync wrapper."""
        return os.listdir(*args, **kwargs)  # noqa: PTH208


async def airmtree(path: str) -> None:
    """Async wrapper for shutil.rmtree.

    Removes a directory tree recursively.

    Args:
        path: Directory to remove recursively.
    """
    await asyncio.to_thread(shutil.rmtree, path)


async def airmdir(path: str) -> None:
    """Async wrapper for os.rmdir.

    Removes an empty directory.

    Args:
        path: Empty directory to remove.
    """
    await asyncio.to_thread(os.rmdir, path)


async def aioremove(path: str | os.PathLike) -> None:
    """Async wrapper for os.remove.

    Removes a file.

    Args:
        path: File to remove.
    """
    await asyncio.to_thread(os.remove, path)


async def graceful_cancel_tasks(
    tasks: list[asyncio.Task],
    timeout: float = 1.0,  # noqa: ASYNC109
) -> None:
    """Cancel tasks with graceful timeout, then force cancel remaining.

    This is the standard shutdown pattern for async tasks:
    1. Wait up to `timeout` seconds for tasks to complete gracefully
    2. Force cancel any tasks still running
    3. Await all cancelled tasks to ensure cleanup

    Args:
        tasks: List of tasks to cancel (filters out already-done tasks)
        timeout: Seconds to wait for graceful completion (default: 1.0)
    """
    pending = [t for t in tasks if not t.done()]
    if not pending:
        return

    # Wait for graceful completion
    _, still_pending = await asyncio.wait(
        pending,
        timeout=timeout,
        return_when=asyncio.ALL_COMPLETED,
    )

    # Force cancel remaining
    for task in still_pending:
        task.cancel()

    # Await all cancelled tasks
    for task in still_pending:
        with contextlib.suppress(asyncio.CancelledError):
            await task


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


class TaskManager:
    """Manages async tasks with proper lifecycle handling.

    Provides consistent start/stop behavior with graceful shutdown:
    1. Set running=False and signal stop event (graceful)
    2. Wait with timeout for tasks to complete
    3. Cancel remaining tasks if still alive
    4. Always await to completion

    Similar to ManagedProcess but for asyncio Tasks instead of subprocesses.

    Usage:
        # Single background loop
        self._tasks = TaskManager()

        async def on_reload(self):
            self._tasks.start()
            self._tasks.create(self._main_loop())

        async def _main_loop(self):
            while self._tasks.running:
                await self.do_work()
                if await self._tasks.sleep(60):
                    break  # Stop requested

        async def exit(self):
            await self._tasks.stop()

    Keyed tasks (for per-item tracking like scratchpad hysteresis):
        self._tasks.create(self._delayed_hide(uid), key=uid)
        self._tasks.cancel_keyed(uid)  # Cancel specific task
    """

    def __init__(
        self,
        graceful_timeout: float = 1.0,
        on_error: Callable[[asyncio.Task, BaseException], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        """Initialize.

        Args:
            graceful_timeout: Seconds to wait for graceful stop before force cancel
            on_error: Async callback when a task fails (receives task and exception)
        """
        self._tasks: list[asyncio.Task] = []
        self._keyed_tasks: dict[str, asyncio.Task] = {}
        self._running: bool = False
        self._stop_event: asyncio.Event | None = None
        self._graceful_timeout = graceful_timeout
        self._on_error = on_error

    @property
    def running(self) -> bool:
        """Check if manager is running (tasks should continue)."""
        return self._running

    def start(self) -> None:
        """Mark manager as running. Call before creating tasks."""
        self._running = True
        self._stop_event = asyncio.Event()

    def create(self, coro: Coroutine[Any, Any, Any], *, key: str | None = None) -> asyncio.Task:
        """Create and track a task.

        Args:
            coro: Coroutine to run
            key: Optional key for keyed task (replaces existing task with same key)

        Returns:
            The created task
        """
        if key is not None:
            self.cancel_keyed(key)
            task = asyncio.create_task(self._wrap_task(coro))
            self._keyed_tasks[key] = task
        else:
            task = asyncio.create_task(self._wrap_task(coro))
            self._tasks.append(task)
        return task

    async def _wrap_task(self, coro: Coroutine[Any, Any, Any]) -> None:
        """Wrap a coroutine to handle errors via callback."""
        try:
            await coro
        except asyncio.CancelledError:
            raise
        except BaseException as e:  # pylint: disable=broad-exception-caught
            if self._on_error:
                task = asyncio.current_task()
                assert task is not None
                await self._on_error(task, e)
            else:
                raise

    def cancel_keyed(self, key: str) -> bool:
        """Cancel a keyed task immediately.

        Args:
            key: The task key

        Returns:
            True if task existed and was cancelled
        """
        task = self._keyed_tasks.pop(key, None)
        if task and not task.done():
            task.cancel()
            return True
        return False

    async def sleep(self, duration: float) -> bool:
        """Interruptible sleep that respects stop signal.

        Use this instead of asyncio.sleep() in loops.

        Args:
            duration: Sleep duration in seconds

        Returns:
            True if interrupted (should exit loop), False if completed normally
        """
        if self._stop_event is None:
            await asyncio.sleep(duration)
            return not self._running
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=duration)
        except TimeoutError:
            return False  # Sleep completed normally
        return True  # Stop event was set

    async def stop(self) -> None:
        """Stop all tasks with graceful timeout.

        Shutdown sequence (mirrors ManagedProcess):
        1. Set running=False and signal stop event (graceful)
        2. Wait up to graceful_timeout for tasks to complete
        3. Cancel remaining tasks if still alive
        4. Await all tasks to completion
        """
        self._running = False
        if self._stop_event:
            self._stop_event.set()

        all_tasks = self._tasks + list(self._keyed_tasks.values())
        await graceful_cancel_tasks(all_tasks, timeout=self._graceful_timeout)

        self._tasks.clear()
        self._keyed_tasks.clear()
        self._stop_event = None
