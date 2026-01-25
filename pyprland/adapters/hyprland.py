"""Hyprland adapter."""

from logging import Logger
from typing import Any, cast

from ..constants import DEFAULT_NOTIFICATION_DURATION_MS
from ..ipc import get_response, hyprctl_connection, retry_on_reset
from ..models import ClientInfo, MonitorInfo
from .backend import EnvironmentBackend


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

    @retry_on_reset
    async def execute(self, command: str | list | dict, *, log: Logger, **kwargs: Any) -> bool:  # noqa: ANN401
        """Execute a command (or list of commands).

        Args:
            command: The command to execute
            log: Logger to use for this operation
            **kwargs: Additional arguments (base_command, weak, etc.)
        """
        base_command = kwargs.get("base_command", "dispatch")
        weak = kwargs.get("weak", False)

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
            resp = await ctl_reader.read(100)

        # remove "\n" from the response
        resp = b"".join(resp.split(b"\n"))

        r: bool = resp == b"ok" * nb_cmds
        if not r:
            if weak:
                log.warning("FAILED %s", resp)
            else:
                log.error("FAILED %s", resp)
        return r

    @retry_on_reset
    async def execute_json(self, command: str, *, log: Logger, **kwargs: Any) -> Any:  # noqa: ANN401, ARG002
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
            and (workspace is None or cast("str", client["workspace"]["name"]) == workspace)
            and (workspace_bl is None or cast("str", client["workspace"]["name"]) != workspace_bl)
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

    def parse_event(self, raw_data: str, *, log: Logger) -> tuple[str, Any] | None:  # noqa: ARG002
        """Parse a raw event string into (event_name, event_data).

        Args:
            raw_data: Raw event string from the compositor
            log: Logger to use for this operation (unused in Hyprland - simple parsing)
        """
        if ">>" not in raw_data:
            return None
        cmd, params = raw_data.split(">>", 1)
        return f"event_{cmd}", params.rstrip("\n")

    async def notify(self, message: str, duration: int = DEFAULT_NOTIFICATION_DURATION_MS, color: str = "ff1010", *, log: Logger) -> None:
        """Send a notification.

        Args:
            message: The notification message
            duration: Duration in milliseconds
            color: Hex color code
            log: Logger to use for this operation
        """
        # Using icon -1 for default/generic
        await self._notify_impl(message, duration, color, -1, log=log)

    async def notify_info(self, message: str, duration: int = DEFAULT_NOTIFICATION_DURATION_MS, *, log: Logger) -> None:
        """Send an info notification.

        Args:
            message: The notification message
            duration: Duration in milliseconds
            log: Logger to use for this operation
        """
        # Using icon 1 for info
        await self._notify_impl(message, duration, "1010ff", 1, log=log)

    async def notify_error(self, message: str, duration: int = DEFAULT_NOTIFICATION_DURATION_MS, *, log: Logger) -> None:
        """Send an error notification.

        Args:
            message: The notification message
            duration: Duration in milliseconds
            log: Logger to use for this operation
        """
        # Using icon 0 for error
        await self._notify_impl(message, duration, "ff1010", 0, log=log)

    async def _notify_impl(self, text: str, duration: int, color: str, icon: int, *, log: Logger) -> None:
        """Internal notify implementation.

        Args:
            text: The notification text
            duration: Duration in milliseconds
            color: Hex color code
            icon: Icon code (-1 default, 0 error, 1 info)
            log: Logger to use for this operation
        """
        # This mirrors ipc.notify logic for Hyprland
        await self.execute(f"{icon} {duration} rgb({color})  {text}", log=log, base_command="notify")
