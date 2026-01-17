"""Hyprland adapter."""

from typing import Any, cast

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
    async def execute(self, command: str | list | dict, **kwargs: Any) -> bool:  # noqa: ANN401
        """Execute a command (or list of commands)."""
        base_command = kwargs.get("base_command", "dispatch")
        weak = kwargs.get("weak", False)

        if not command:
            self.log.warning("%s triggered without a command!", base_command)
            return False
        self.log.debug("%s %s", base_command, command)

        async with hyprctl_connection(self.log) as (ctl_reader, ctl_writer):
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
                self.log.warning("FAILED %s", resp)
            else:
                self.log.error("FAILED %s", resp)
        return r

    @retry_on_reset
    async def execute_json(self, command: str, **kwargs: Any) -> Any:  # noqa: ANN401, ARG002
        """Execute a command and return the JSON result."""
        ret = await get_response(f"-j/{command}".encode(), self.log)
        assert isinstance(ret, list | dict)
        return ret

    async def get_clients(
        self,
        mapped: bool = True,
        workspace: str | None = None,
        workspace_bl: str | None = None,
    ) -> list[ClientInfo]:
        """Return the list of clients, optionally filtered."""
        return [
            client
            for client in cast("list[ClientInfo]", await self.execute_json("clients"))
            if (not mapped or client["mapped"])
            and (workspace is None or cast("str", client["workspace"]["name"]) == workspace)
            and (workspace_bl is None or cast("str", client["workspace"]["name"]) != workspace_bl)
        ]

    async def get_monitors(self) -> list[MonitorInfo]:
        """Return the list of monitors."""
        return cast("list[MonitorInfo]", await self.execute_json("monitors"))

    async def execute_batch(self, commands: list[str]) -> None:
        """Execute a batch of commands."""
        if not commands:
            return

        self.log.debug("Batch %s", commands)

        # Format commands for batch execution
        # Based on ipc.py _format_command implementation
        formatted_cmds = [f"dispatch {command}" for command in commands]

        async with hyprctl_connection(self.log) as (_, ctl_writer):
            ctl_writer.write(f"[[BATCH]] {' ; '.join(formatted_cmds)}".encode())
            await ctl_writer.drain()
            # We assume it worked, similar to current implementation
            # detailed error checking for batch is limited in current ipc.py implementation

    def parse_event(self, raw_data: str) -> tuple[str, Any] | None:
        """Parse a raw event string into (event_name, event_data)."""
        if ">>" not in raw_data:
            return None
        cmd, params = raw_data.split(">>", 1)
        return f"event_{cmd}", params.rstrip("\n")

    async def notify(self, message: str, duration: int = 5000, color: str = "ff1010") -> None:
        """Send a notification."""
        # Using icon -1 for default/generic
        await self._notify_impl(message, duration, color, -1)

    async def notify_info(self, message: str, duration: int = 5000) -> None:
        """Send an info notification."""
        # Using icon 1 for info
        await self._notify_impl(message, duration, "1010ff", 1)

    async def notify_error(self, message: str, duration: int = 5000) -> None:
        """Send an error notification."""
        # Using icon 0 for error
        await self._notify_impl(message, duration, "ff1010", 0)

    async def _notify_impl(self, text: str, duration: int, color: str, icon: int) -> None:
        """Internal notify implementation."""
        # This mirrors ipc.notify logic for Hyprland
        await self.execute(f"{icon} {duration} rgb({color})  {text}", base_command="notify")
