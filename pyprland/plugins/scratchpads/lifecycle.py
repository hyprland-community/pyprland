"""Scratchpad lifecycle management mixin."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, cast

from ...common import apply_variables

if TYPE_CHECKING:
    import logging

    from ...adapters.proxy import BackendProxy
    from ...common import SharedState
    from ...models import ClientInfo
    from .lookup import ScratchDB
    from .objects import Scratch

__all__ = ["LifecycleMixin"]


class LifecycleMixin:
    """Mixin for scratchpad process lifecycle management.

    Handles starting, stopping, and monitoring scratchpad processes.
    """

    # Type hints for attributes provided by the composed class
    log: logging.Logger
    backend: BackendProxy
    scratches: ScratchDB
    procs: dict[str, asyncio.subprocess.Process]
    state: SharedState

    # Methods provided by the composed class
    async def _configure_windowrules(self, scratch: Scratch) -> None:
        """Configure window rules for a scratchpad."""
        _ = scratch  # stub, overridden by composed class

    async def _unset_windowrules(self, scratch: Scratch) -> None:
        """Unset window rules for a scratchpad."""
        _ = scratch  # stub, overridden by composed class

    async def __wait_for_client(self, scratch: Scratch, use_proc: bool = True) -> bool:
        """Wait for a client to be up and running.

        if `match_by=` is used, will use the match criteria, else the process's PID will be used.

        Args:
            scratch: The scratchpad object
            use_proc: whether to use the process object
        """
        self.log.info("==> Wait for %s spawning", scratch.uid)
        interval_range = [0.1] * 10 + [0.2] * 20 + [0.5] * 15
        for interval in interval_range:
            await asyncio.sleep(interval)
            is_alive = await scratch.is_alive()

            # skips the checks if the process isn't started (just wait)
            if is_alive or not use_proc:
                info = await scratch.fetch_matching_client()
                if info:
                    await scratch.update_client_info(info)
                    self.log.info(
                        "=> %s client (proc:%s, addr:%s) detected on time",
                        scratch.uid,
                        scratch.pid,
                        scratch.full_address,
                    )
                    self.scratches.register(scratch)
                    self.scratches.clear_state(scratch, "respawned")
                    return True
            if use_proc and not is_alive:
                return False
        return False

    async def _start_scratch_nopid(self, scratch: Scratch) -> bool:
        """Ensure alive, PWA version.

        Args:
            scratch: The scratchpad object
        """
        uid = scratch.uid
        started = scratch.meta.no_pid
        if not await scratch.is_alive():
            started = False
        if not started:
            self.scratches.reset(scratch)
            await self.start_scratch_command(uid)
            r = await self.__wait_for_client(scratch, use_proc=False)
            scratch.meta.no_pid = r
            return r
        return True

    async def _start_scratch(self, scratch: Scratch) -> bool:
        """Ensure alive, standard version.

        Args:
            scratch: The scratchpad object
        """
        uid = scratch.uid
        if uid in self.procs:
            with contextlib.suppress(ProcessLookupError):
                self.procs[uid].kill()
            del self.procs[uid]  # ensure the old process is removed from the dict
        self.scratches.reset(scratch)
        await self.start_scratch_command(uid)
        self.log.info("starting %s", uid)
        if not await self.__wait_for_client(scratch):
            self.log.error("⚠ Failed spawning %s as proc %s", uid, scratch.pid)
            if await scratch.is_alive():
                error = "The command didn't open a window"
            else:
                await self.procs[uid].communicate()
                code = self.procs[uid].returncode
                error = f"The command failed with code {code}" if code else "The command terminated successfully, is it already running?"
            self.log.error('"%s": %s', scratch.conf["command"], error)
            await self.backend.notify_error(error)
            return False
        return True

    async def ensure_alive(self, uid: str) -> bool:
        """Ensure the scratchpad is started.

        Returns true if started

        Args:
            uid: The scratchpad name
        """
        item = self.scratches.get(name=uid)
        assert item

        if not item.have_command:
            return True

        if item.conf.get_bool("process_tracking"):
            if not await item.is_alive():
                await self._configure_windowrules(item)
                self.log.info("%s is not running, starting...", uid)
                if not await self._start_scratch(item):
                    await self.backend.notify_error(f'Failed to show scratch "{item.uid}"')
                    return False
            await self._unset_windowrules(item)
            return True

        return await self._start_scratch_nopid(item)

    async def start_scratch_command(self, name: str) -> None:
        """Spawn a given scratchpad's process.

        Args:
            name: The scratchpad name
        """
        scratch = self.scratches.get(name)
        assert scratch
        self.scratches.set_state(scratch, "respawned")
        old_pid = self.procs[name].pid if name in self.procs else 0
        command = apply_variables(scratch.conf.get_str("command"), self.state.variables)
        proc = await asyncio.create_subprocess_shell(command)
        self.procs[name] = proc
        pid = proc.pid
        scratch.reset(pid)
        self.scratches.register(scratch, pid=pid)
        self.log.info("scratch %s (%s) has pid %s", scratch.uid, scratch.conf.get("command"), pid)
        if old_pid:
            self.scratches.clear(pid=old_pid)

    async def update_scratch_info(self, orig_scratch: Scratch | None = None) -> None:
        """Update Scratchpad information.

        If `scratch` is given, update only this scratchpad.
        Else, update every scratchpad.

        Args:
            orig_scratch: The scratchpad object
        """
        pid = orig_scratch.pid if orig_scratch else None
        for client in await self.backend.execute_json("clients"):
            assert isinstance(client, dict)
            if pid and pid != client["pid"]:
                continue
            # if no address registered, register it
            # + update client info in any case
            scratch = self.scratches.get(addr=client["address"][2:])
            if not scratch and client["pid"]:
                scratch = self.scratches.get(pid=client["pid"])
            if scratch:
                self.scratches.register(scratch, addr=client["address"][2:])
                await scratch.update_client_info(cast("ClientInfo", client))
                break
        else:
            self.log.info("Didn't update scratch info %s", self)
