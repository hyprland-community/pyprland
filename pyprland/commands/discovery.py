"""Command extraction and discovery from plugins."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

from .models import CLIENT_COMMANDS, CommandInfo
from .parsing import parse_docstring

if TYPE_CHECKING:
    from ..manager import Pyprland

__all__ = ["extract_commands_from_object", "get_all_commands", "get_client_commands"]


def extract_commands_from_object(obj: object, source: str) -> list[CommandInfo]:
    """Extract commands from a plugin class or instance.

    Works with both classes (for docs generation) and instances (runtime).
    Looks for methods starting with "run_" and extracts their docstrings.

    Args:
        obj: A plugin class or instance
        source: The source identifier (plugin name, "built-in", or "client")

    Returns:
        List of CommandInfo objects
    """
    commands: list[CommandInfo] = []

    for name in dir(obj):
        if not name.startswith("run_"):
            continue

        method = getattr(obj, name)
        if not callable(method):
            continue

        command_name = name[4:]  # Remove 'run_' prefix
        docstring = inspect.getdoc(method) or ""

        args, short_desc, full_desc = parse_docstring(docstring)

        commands.append(
            CommandInfo(
                name=command_name,
                args=args,
                short_description=short_desc,
                full_description=full_desc,
                source=source,
            )
        )

    return commands


def get_client_commands() -> list[CommandInfo]:
    """Get client-only commands (edit, validate).

    These commands run on the client side and don't go through the daemon.

    Returns:
        List of CommandInfo for client-only commands
    """
    commands: list[CommandInfo] = []
    for name, doc in CLIENT_COMMANDS.items():
        args, short_desc, full_desc = parse_docstring(doc)
        commands.append(
            CommandInfo(
                name=name,
                args=args,
                short_description=short_desc,
                full_description=full_desc,
                source="client",
            )
        )
    return commands


def get_all_commands(manager: Pyprland) -> dict[str, CommandInfo]:
    """Get all commands from plugins and client.

    Args:
        manager: The Pyprland manager instance with loaded plugins

    Returns:
        Dict mapping command name to CommandInfo
    """
    commands: dict[str, CommandInfo] = {}

    # Extract from all plugins
    for plugin in manager.plugins.values():
        source = "built-in" if plugin.name == "pyprland" else plugin.name
        for cmd in extract_commands_from_object(plugin, source):
            commands[cmd.name] = cmd

    # Add client-only commands
    for cmd in get_client_commands():
        commands[cmd.name] = cmd

    return commands
