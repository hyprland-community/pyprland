"""Process lifecycle management utilities for spawning subprocesses.

ManagedProcess:
    Manages a subprocess with proper lifecycle (SIGTERM -> wait -> SIGKILL).
    Provides start/stop/restart and stdout iteration helpers.

SupervisedProcess:
    Extends ManagedProcess with automatic restart on crash, cooldown
    periods to prevent restart loops, and crash event callbacks.
"""

__all__ = ["ManagedProcess", "SupervisedProcess"]

import asyncio
import contextlib
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any


class ManagedProcess:
    """Manages a subprocess with proper lifecycle handling.

    Provides consistent start/stop behavior with graceful shutdown:
    1. SIGTERM first (graceful)
    2. Wait with timeout
    3. SIGKILL if still alive
    4. Always wait() to reap zombie

    Usage:
        proc = ManagedProcess()
        await proc.start("sleep 100")

        # Access underlying process if needed
        if proc.process and proc.process.stdout:
            line = await proc.process.stdout.readline()

        # Or use iter_lines() helper
        async for line in proc.iter_lines():
            print(line)

        await proc.stop()
    """

    def __init__(self, graceful_timeout: float = 1.0) -> None:
        """Initialize.

        Args:
            graceful_timeout: Seconds to wait after SIGTERM before SIGKILL
        """
        self._proc: asyncio.subprocess.Process | None = None
        self._command: str | None = None
        self._graceful_timeout = graceful_timeout
        self._subprocess_kwargs: dict[str, Any] = {}

    @property
    def pid(self) -> int | None:
        """Return PID if process exists, else None."""
        return self._proc.pid if self._proc else None

    @property
    def returncode(self) -> int | None:
        """Return exit code if process exited, else None."""
        return self._proc.returncode if self._proc else None

    @property
    def is_alive(self) -> bool:
        """Check if process is currently running."""
        return self._proc is not None and self._proc.returncode is None

    @property
    def process(self) -> asyncio.subprocess.Process | None:
        """Access underlying process for advanced use (e.g., stdin/stdout)."""
        return self._proc

    async def start(
        self,
        command: str,
        **subprocess_kwargs: Any,
    ) -> None:
        """Start the process. Stops existing process first if running.

        Args:
            command: Shell command to run
            **subprocess_kwargs: Passed to create_subprocess_shell (e.g., stdout=PIPE)
        """
        if self.is_alive:
            await self.stop()

        self._command = command
        self._subprocess_kwargs = subprocess_kwargs
        self._proc = await asyncio.create_subprocess_shell(command, **subprocess_kwargs)

    async def stop(self) -> int | None:
        """Stop the process gracefully.

        Shutdown sequence:
        1. SIGTERM (graceful)
        2. Wait up to graceful_timeout
        3. SIGKILL if still alive
        4. wait() to reap

        Returns:
            The process return code, or None if not running
        """
        if self._proc is None:
            return None

        if self._proc.returncode is not None:
            # Already exited
            return self._proc.returncode

        # 1. Try graceful termination
        with contextlib.suppress(ProcessLookupError):
            self._proc.terminate()

        # 2. Wait with timeout
        try:
            await asyncio.wait_for(self._proc.wait(), timeout=self._graceful_timeout)
        except TimeoutError:
            # 3. Force kill if still alive
            with contextlib.suppress(ProcessLookupError):
                self._proc.kill()
            await self._proc.wait()

        return self._proc.returncode

    async def restart(self) -> None:
        """Restart the process with the same command and kwargs.

        Raises:
            RuntimeError: If no command was previously set via start()
        """
        if self._command is None:
            msg = "Cannot restart: no command was previously started"
            raise RuntimeError(msg)
        await self.start(self._command, **self._subprocess_kwargs)

    async def wait(self) -> int:
        """Wait for process to exit and return exit code.

        Raises:
            RuntimeError: If no process is running
        """
        if self._proc is None:
            msg = "No process running"
            raise RuntimeError(msg)
        return await self._proc.wait()

    async def iter_lines(self) -> AsyncIterator[str]:
        """Iterate over stdout lines.

        Requires process to be started with stdout=asyncio.subprocess.PIPE.

        Yields:
            Decoded, stripped lines from stdout

        Raises:
            RuntimeError: If process has no stdout pipe
        """
        if self._proc is None or self._proc.stdout is None:
            msg = "No process or stdout not piped"
            raise RuntimeError(msg)

        while self._proc.returncode is None:
            line = await self._proc.stdout.readline()
            if not line:
                break
            yield line.decode().strip()


class SupervisedProcess(ManagedProcess):
    """A ManagedProcess with automatic restart on crash.

    Extends ManagedProcess with supervision capabilities:
    - Automatic restart when process exits
    - Cooldown period to prevent restart loops
    - Configurable callbacks for crash events

    Usage:
        async def on_crash(proc, return_code):
            log.warning(f"Process crashed with code {return_code}")

        proc = SupervisedProcess(
            cooldown=60.0,
            on_crash=on_crash,
        )
        await proc.start("my-daemon")

        # Process will auto-restart on crash
        # Call stop() to permanently stop
        await proc.stop()
    """

    def __init__(
        self,
        graceful_timeout: float = 1.0,
        cooldown: float = 60.0,
        min_runtime: float = 0.0,
        on_crash: Callable[["SupervisedProcess", int], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        """Initialize.

        Args:
            graceful_timeout: Seconds to wait after SIGTERM before SIGKILL
            cooldown: Minimum seconds between restarts (if process runs shorter, delay is added)
            min_runtime: Process must run at least this long or cooldown is applied.
                         Defaults to cooldown value if not specified.
            on_crash: Async callback when process crashes (receives self and return_code)
        """
        super().__init__(graceful_timeout)
        self._cooldown = cooldown
        self._min_runtime = min_runtime or cooldown
        self._on_crash = on_crash
        self._supervisor_task: asyncio.Task[None] | None = None
        self._running = False

    @property
    def is_supervised(self) -> bool:
        """Check if supervision loop is active."""
        return self._running and self._supervisor_task is not None

    async def start(
        self,
        command: str,
        **subprocess_kwargs: Any,
    ) -> None:
        """Start the supervised process.

        Starts the process and begins supervision. If the process crashes,
        it will be restarted automatically (subject to cooldown).

        Args:
            command: Shell command to run
            **subprocess_kwargs: Passed to create_subprocess_shell
        """
        # Stop any existing supervision
        await self.stop()

        self._command = command
        self._subprocess_kwargs = subprocess_kwargs
        self._running = True

        self._supervisor_task = asyncio.create_task(self._supervise())

    async def _supervise(self) -> None:
        """Internal supervision loop."""
        assert self._command is not None, "_supervise called without command"
        while self._running:
            start_time = asyncio.get_event_loop().time()

            # Start the process
            self._proc = await asyncio.create_subprocess_shell(
                self._command,
                **self._subprocess_kwargs,
            )

            # Wait for it to exit
            await self._proc.wait()

            # Check if we should continue supervision
            # (self._running may have been set to False during stop())
            if self._running:
                # Process crashed - calculate delay
                elapsed = asyncio.get_event_loop().time() - start_time

                if self._on_crash:
                    await self._on_crash(self, self._proc.returncode or -1)

                if elapsed < self._min_runtime:
                    # Crashed too quickly - apply cooldown
                    delay = max(0.1, (self._cooldown - elapsed) / 2)
                    await asyncio.sleep(delay)
                else:
                    # Ran long enough - restart immediately
                    await asyncio.sleep(0.1)

    async def stop(self) -> int | None:
        """Stop the supervised process permanently.

        Cancels the supervision loop and stops the process.

        Returns:
            The process return code, or None if not running
        """
        self._running = False

        if self._supervisor_task:
            self._supervisor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._supervisor_task
            self._supervisor_task = None

        return await super().stop()
