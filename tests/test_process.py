"""Tests for process lifecycle management utilities."""

import asyncio

import pytest

from pyprland.process import ManagedProcess, SupervisedProcess


class TestManagedProcess:
    """Tests for ManagedProcess."""

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        """Test basic start and stop lifecycle."""
        proc = ManagedProcess()
        assert not proc.is_alive
        assert proc.pid is None

        await proc.start("sleep 10")
        assert proc.is_alive
        assert proc.pid is not None

        returncode = await proc.stop()
        assert not proc.is_alive
        # SIGTERM returns negative signal number or None depending on platform
        assert returncode is not None

    @pytest.mark.asyncio
    async def test_stop_not_started(self):
        """Test stop when never started returns None."""
        proc = ManagedProcess()
        result = await proc.stop()
        assert result is None

    @pytest.mark.asyncio
    async def test_stop_already_exited(self):
        """Test stop on already exited process."""
        proc = ManagedProcess()
        await proc.start("true")  # Exits immediately
        await asyncio.sleep(0.1)  # Let it exit

        returncode = await proc.stop()
        assert returncode == 0

    @pytest.mark.asyncio
    async def test_start_stops_existing(self):
        """Test that start() stops existing process first."""
        proc = ManagedProcess()
        await proc.start("sleep 10")
        first_pid = proc.pid

        await proc.start("sleep 10")
        second_pid = proc.pid

        assert first_pid != second_pid
        await proc.stop()

    @pytest.mark.asyncio
    async def test_restart(self):
        """Test restart with same command."""
        proc = ManagedProcess()
        await proc.start("sleep 10")
        first_pid = proc.pid

        await proc.restart()
        second_pid = proc.pid

        assert first_pid != second_pid
        assert proc.is_alive
        await proc.stop()

    @pytest.mark.asyncio
    async def test_restart_without_start_raises(self):
        """Test restart without prior start raises RuntimeError."""
        proc = ManagedProcess()
        with pytest.raises(RuntimeError, match="no command"):
            await proc.restart()

    @pytest.mark.asyncio
    async def test_wait(self):
        """Test wait for process completion."""
        proc = ManagedProcess()
        await proc.start("sleep 0.1")

        returncode = await proc.wait()
        assert returncode == 0
        assert not proc.is_alive

    @pytest.mark.asyncio
    async def test_wait_without_start_raises(self):
        """Test wait without process raises RuntimeError."""
        proc = ManagedProcess()
        with pytest.raises(RuntimeError, match="No process"):
            await proc.wait()

    @pytest.mark.asyncio
    async def test_returncode(self):
        """Test returncode property."""
        proc = ManagedProcess()
        assert proc.returncode is None

        await proc.start("exit 42")
        await proc.wait()
        assert proc.returncode == 42

    @pytest.mark.asyncio
    async def test_iter_lines(self):
        """Test iterating over stdout lines."""
        proc = ManagedProcess()
        await proc.start("echo -e 'line1\nline2\nline3'", stdout=asyncio.subprocess.PIPE)

        lines = [line async for line in proc.iter_lines()]
        assert lines == ["line1", "line2", "line3"]

    @pytest.mark.asyncio
    async def test_iter_lines_no_stdout_raises(self):
        """Test iter_lines without stdout pipe raises."""
        proc = ManagedProcess()
        await proc.start("echo hello")

        with pytest.raises(RuntimeError, match="stdout not piped"):
            async for _ in proc.iter_lines():
                pass

        await proc.stop()

    @pytest.mark.asyncio
    async def test_iter_lines_not_started_raises(self):
        """Test iter_lines without process raises."""
        proc = ManagedProcess()
        with pytest.raises(RuntimeError, match="No process"):
            async for _ in proc.iter_lines():
                pass

    @pytest.mark.asyncio
    async def test_graceful_timeout(self):
        """Test that process is killed after graceful timeout."""
        # Use a process that ignores SIGTERM
        proc = ManagedProcess(graceful_timeout=0.2)
        await proc.start("trap '' TERM; sleep 10")

        # stop() should kill after timeout
        returncode = await proc.stop()
        assert not proc.is_alive
        assert returncode is not None

    @pytest.mark.asyncio
    async def test_process_property(self):
        """Test accessing underlying process."""
        proc = ManagedProcess()
        assert proc.process is None

        await proc.start("sleep 10")
        assert proc.process is not None
        assert proc.process.pid == proc.pid

        await proc.stop()


class TestSupervisedProcess:
    """Tests for SupervisedProcess."""

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        """Test basic supervised start and stop."""
        proc = SupervisedProcess()
        await proc.start("sleep 10")

        # Wait for process to actually start (it's in a background task)
        await asyncio.sleep(0.1)

        assert proc.is_alive
        assert proc.is_supervised

        await proc.stop()
        assert not proc.is_alive
        assert not proc.is_supervised

    @pytest.mark.asyncio
    async def test_auto_restart(self):
        """Test that process auto-restarts on crash."""
        restart_count = 0

        async def on_crash(proc: SupervisedProcess, code: int) -> None:
            nonlocal restart_count
            restart_count += 1

        proc = SupervisedProcess(
            cooldown=0.1,
            min_runtime=0.0,
            on_crash=on_crash,
        )

        # Start a process that exits immediately
        await proc.start("exit 1")

        # Wait for a couple restarts
        await asyncio.sleep(0.5)

        await proc.stop()

        # Should have restarted multiple times
        assert restart_count >= 2

    @pytest.mark.asyncio
    async def test_cooldown(self):
        """Test that cooldown delays restarts for short-lived processes."""
        crash_times: list[float] = []

        async def on_crash(proc: SupervisedProcess, code: int) -> None:
            crash_times.append(asyncio.get_event_loop().time())

        proc = SupervisedProcess(
            cooldown=1.0,
            min_runtime=0.5,
            on_crash=on_crash,
        )

        await proc.start("exit 1")

        # Wait for 2 crashes
        while len(crash_times) < 2:
            await asyncio.sleep(0.1)

        await proc.stop()

        # Second crash should be delayed due to cooldown
        time_between = crash_times[1] - crash_times[0]
        assert time_between >= 0.2  # At least some delay

    @pytest.mark.asyncio
    async def test_on_crash_receives_returncode(self):
        """Test that on_crash callback receives correct return code."""
        received_codes: list[int] = []

        async def on_crash(proc: SupervisedProcess, code: int) -> None:
            received_codes.append(code)

        proc = SupervisedProcess(
            cooldown=0.1,
            min_runtime=0.0,
            on_crash=on_crash,
        )

        await proc.start("exit 42")

        # Wait for at least one crash
        while not received_codes:
            await asyncio.sleep(0.1)

        await proc.stop()

        assert 42 in received_codes

    @pytest.mark.asyncio
    async def test_stop_cancels_supervision(self):
        """Test that stop() properly cancels the supervision task."""
        proc = SupervisedProcess()
        await proc.start("sleep 10")

        assert proc._supervisor_task is not None
        assert not proc._supervisor_task.done()

        await proc.stop()

        assert proc._supervisor_task is None
        assert not proc.is_supervised

    @pytest.mark.asyncio
    async def test_start_stops_previous(self):
        """Test that start() stops previous supervision."""
        proc = SupervisedProcess()
        await proc.start("sleep 10")
        first_task = proc._supervisor_task

        await proc.start("sleep 10")
        second_task = proc._supervisor_task

        assert first_task != second_task
        assert first_task is None or first_task.done()

        await proc.stop()

    @pytest.mark.asyncio
    async def test_no_on_crash_callback(self):
        """Test supervision works without on_crash callback."""
        proc = SupervisedProcess(
            cooldown=0.1,
            min_runtime=0.0,
        )

        await proc.start("exit 1")
        await asyncio.sleep(0.3)

        # Should still be supervised even without callback
        assert proc.is_supervised

        await proc.stop()
