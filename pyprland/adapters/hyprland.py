"""Hyprland compositor backend implementation.

Primary backend for Hyprland, using its Unix socket IPC protocol.
Provides full functionality including batched commands, JSON queries,
and Hyprland-specific event parsing.
"""

from logging import Logger
from typing import Any, cast

from ..ipc import get_response, hyprctl_connection, retry_on_reset
from ..models import ClientInfo, MonitorInfo
from .backend import EnvironmentBackend
from .lua_translate import dispatch_to_lua_call, keyword_to_lua_code
from .notifier import HyprlandNotifier, Notifier


class HyprlandBackend(EnvironmentBackend):
    """Hyprland backend implementation."""

    def _format_command(self, command_list: list[str] | list[list[str]], default_base_command: str) -> list[str]:
        """Format a list of commands to be sent to Hyprland."""
        result = []
        for command in command_list:
            if isinstance(command, str):
                result.append(f"{default_base_command} {command}")
            else:
                result.append(f"{command[1]} {command[0]}")
        return result

    def _translate_commands(self, command: str | list[str], base_command: str, log: Logger) -> tuple[str | list[str], str]:
        """Translate legacy IPC commands to Lua equivalents for the Lua config parser.

        keyword → eval with hl.config/hl.window_rule/etc.
        dispatch → eval with hl.dispatch(hl.dsp.*({...}))
        """
        if base_command == "keyword":
            translator = keyword_to_lua_code
            wrap_dispatch = False
            warn_label = "keyword"
        else:
            translator = dispatch_to_lua_call
            wrap_dispatch = True
            warn_label = "dispatch"
        new_base = "eval"

        if isinstance(command, list):
            translated = []
            for cmd in command:
                if isinstance(cmd, str):
                    result = translator(cmd)
                    if result:
                        translated.append(f"hl.dispatch({result})" if wrap_dispatch else result)
                    else:
                        log.warning("No Lua translation for %s: %s", warn_label, cmd)
                        translated.append(cmd)
                else:
                    translated.append(cmd)
            return translated, new_base

        result = translator(command)
        if result:
            return f"hl.dispatch({result})" if wrap_dispatch else result, new_base
        log.warning("No Lua translation for %s: %s", warn_label, command)
        return command, base_command

    @retry_on_reset
    async def execute(self, command: str | list | dict, *, log: Logger, **kwargs: Any) -> bool:
        """Execute a command (or list of commands).

        Args:
            command: The command to execute
            log: Logger to use for this operation
            **kwargs: Additional arguments (base_command, weak, etc.)
        """
        base_command = kwargs.get("base_command", "dispatch")
        weak = kwargs.get("weak", False)

        # Lua config mode: translate dispatch/keyword commands to Lua equivalents
        if self.state.lua_mode and base_command in ("keyword", "dispatch") and isinstance(command, (str, list)):
            command, base_command = self._translate_commands(command, base_command, log)

        if not command:
            log.warning("%s triggered without a command!", base_command)
            return False
        log.debug("%s %s", base_command, command)

        async with hyprctl_connection(log) as (ctl_reader, ctl_writer):
            if isinstance(command, list):
                nb_cmds = len(command)
                ctl_writer.write(f"[[BATCH]] {' ; '.join(self._format_command(command, base_command))}".encode())
            else:
                nb_cmds = 1
                ctl_writer.write(f"/{base_command} {command}".encode())
            await ctl_writer.drain()
            resp = await ctl_reader.read(4096)

        # remove "\n" from the response
        resp = b"".join(resp.split(b"\n"))

        r: bool = resp == b"ok" * nb_cmds if base_command != "eval" else not resp.startswith(b"error:")
        if not r:
            if weak:
                log.warning("FAILED %s", resp)
            else:
                log.error("FAILED %s", resp)
        return r

    @retry_on_reset
    async def execute_json(self, command: str, *, log: Logger, **kwargs: Any) -> Any:
        """Execute a command and return the JSON result.

        Args:
            command: The command to execute
            log: Logger to use for this operation
            **kwargs: Additional arguments
        """
        ret = await get_response(f"-j/{command}".encode(), log)
        assert isinstance(ret, list | dict)
        return ret

    async def get_clients(
        self,
        mapped: bool = True,
        workspace: str | None = None,
        workspace_bl: str | None = None,
        *,
        log: Logger,
    ) -> list[ClientInfo]:
        """Return the list of clients, optionally filtered.

        Args:
            mapped: If True, only return mapped clients
            workspace: Filter to this workspace name
            workspace_bl: Blacklist this workspace name
            log: Logger to use for this operation
        """
        return [
            client
            for client in cast("list[ClientInfo]", await self.execute_json("clients", log=log))
            if (not mapped or client["mapped"])
            and (workspace is None or client["workspace"]["name"] == workspace)
            and (workspace_bl is None or client["workspace"]["name"] != workspace_bl)
        ]

    async def get_monitors(self, *, log: Logger, include_disabled: bool = False) -> list[MonitorInfo]:
        """Return the list of monitors.

        Args:
            log: Logger to use for this operation
            include_disabled: If True, include disabled monitors
        """
        cmd = "monitors all" if include_disabled else "monitors"
        return cast("list[MonitorInfo]", await self.execute_json(cmd, log=log))

    async def execute_batch(self, commands: list[str], *, log: Logger) -> None:
        """Execute a batch of commands.

        Args:
            commands: List of commands to execute
            log: Logger to use for this operation
        """
        if not commands:
            return

        log.debug("Batch %s", commands)

        # Format commands for batch execution
        # Based on ipc.py _format_command implementation
        formatted_cmds = [f"dispatch {command}" for command in commands]

        async with hyprctl_connection(log) as (_, ctl_writer):
            ctl_writer.write(f"[[BATCH]] {' ; '.join(formatted_cmds)}".encode())
            await ctl_writer.drain()
            # We assume it worked, similar to current implementation
            # detailed error checking for batch is limited in current ipc.py implementation

    def parse_event(self, raw_data: str, *, log: Logger) -> tuple[str, Any] | None:
        """Parse a raw event string into (event_name, event_data).

        Args:
            raw_data: Raw event string from the compositor
            log: Logger to use for this operation (unused in Hyprland - simple parsing)
        """
        if ">>" not in raw_data:
            return None
        cmd, params = raw_data.split(">>", 1)
        return f"event_{cmd}", params.rstrip("\n")

    def get_default_notifier(self) -> Notifier:
        """Return Hyprland's native notifier using hyprctl notify."""
        return HyprlandNotifier(self.execute)
