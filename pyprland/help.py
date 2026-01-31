"""Help and documentation functions for pyprland commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .command_registry import get_all_commands

if TYPE_CHECKING:
    from .manager import Pyprland

__all__ = ["get_command_help", "get_commands_help", "get_help"]


def get_commands_help(manager: Pyprland) -> dict[str, str]:
    """Get the available commands and their short documentation.

    Args:
        manager: The Pyprland manager instance

    Returns:
        Dict mapping command name to short description with source suffix
    """
    return {name: f"{cmd.short_description} ({cmd.source})" for name, cmd in sorted(get_all_commands(manager).items())}


def get_help(manager: Pyprland) -> str:
    """Get the help documentation for all commands.

    Args:
        manager: The Pyprland manager instance
    """
    intro = """Syntax: pypr [command]

If the command is omitted, runs the daemon which will start every configured plugin.

Available commands:
"""
    return intro + "\n".join(f" {name:20s} {doc}" for name, doc in get_commands_help(manager).items())


def get_command_help(manager: Pyprland, command: str) -> str:
    """Get detailed help for a specific command.

    Args:
        manager: The Pyprland manager instance
        command: Command name to get help for

    Returns:
        Full docstring with source indicator, or error message if not found
    """
    command = command.replace("-", "_")
    commands = get_all_commands(manager)

    if command in commands:
        cmd = commands[command]
        doc = cmd.full_description
        doc_formatted = doc if doc.endswith("\n") else f"{doc}\n"
        return f"{command} ({cmd.source})\n\n{doc_formatted}"

    return f"Unknown command: {command}\nRun 'pypr help' for available commands.\n"
