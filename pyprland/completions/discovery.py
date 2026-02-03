"""Command completion discovery.

Extracts structured completion data from loaded plugins and configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..command_registry import CommandInfo, CommandNode, build_command_tree, get_all_commands
from ..constants import SUPPORTED_SHELLS
from .models import (
    HINT_ARGS,
    KNOWN_COMPLETIONS,
    SCRATCHPAD_COMMANDS,
    CommandCompletion,
    CompletionArg,
)

if TYPE_CHECKING:
    from ..manager import Pyprland

__all__ = ["get_command_completions"]


def _classify_arg(
    arg_value: str,
    cmd_name: str,
    scratchpad_names: list[str],
) -> tuple[str, list[str]]:
    """Classify an argument and determine its completion type and values.

    Args:
        arg_value: The argument value from docstring (e.g., "next|pause|clear")
        cmd_name: The command name (for context-specific handling)
        scratchpad_names: Available scratchpad names from config

    Returns:
        Tuple of (completion_type, values)
    """
    # Check for pipe-separated choices
    if "|" in arg_value:
        return ("choices", arg_value.split("|"))

    # Check for scratchpad commands with "name" arg
    if arg_value == "name" and cmd_name in SCRATCHPAD_COMMANDS:
        return ("dynamic", scratchpad_names)

    # Check for known completions
    if arg_value in KNOWN_COMPLETIONS:
        return ("choices", KNOWN_COMPLETIONS[arg_value])

    # Check for literal values (like "json")
    if arg_value in ("json",):
        return ("literal", [arg_value])

    # Check for hint args
    if arg_value in HINT_ARGS:
        return ("hint", [HINT_ARGS[arg_value]])

    # Default: no completion, show arg name as hint
    return ("hint", [arg_value])


def _build_completion_args(
    cmd_name: str,
    cmd_info: CommandInfo | None,
    scratchpad_names: list[str],
) -> list[CompletionArg]:
    """Build completion args from a CommandInfo."""
    if cmd_info is None:
        return []
    completion_args: list[CompletionArg] = []
    for pos, arg in enumerate(cmd_info.args, start=1):
        comp_type, values = _classify_arg(arg.value, cmd_name, scratchpad_names)
        completion_args.append(
            CompletionArg(
                position=pos,
                completion_type=comp_type,
                values=values,
                required=arg.required,
                description=arg.value,
            )
        )
    return completion_args


def _build_command_from_node(
    root_name: str,
    node: CommandNode,
    scratchpad_names: list[str],
) -> CommandCompletion:
    """Build a CommandCompletion from a CommandNode."""
    # Build subcommands dict
    subcommands: dict[str, CommandCompletion] = {}
    for child_name, child_node in node.children.items():
        if child_node.info:
            subcommands[child_name] = CommandCompletion(
                name=child_name,
                args=_build_completion_args(child_node.full_name, child_node.info, scratchpad_names),
                description=child_node.info.short_description,
            )

    # Build root command completion
    root_args: list[CompletionArg] = []
    root_desc = ""
    if node.info:
        root_args = _build_completion_args(root_name, node.info, scratchpad_names)
        root_desc = node.info.short_description

    return CommandCompletion(
        name=root_name,
        args=root_args,
        description=root_desc,
        subcommands=subcommands,
    )


def _apply_command_overrides(commands: dict[str, CommandCompletion], manager: Pyprland) -> None:
    """Apply special overrides for built-in commands (help, compgen, doc)."""
    all_cmd_names = sorted(commands.keys())

    # Build subcommand completions for help
    help_subcommands: dict[str, CommandCompletion] = {}
    for cmd_name, cmd in commands.items():
        if cmd.subcommands:
            help_subcommands[cmd_name] = CommandCompletion(
                name=cmd_name,
                args=[
                    CompletionArg(
                        position=1,
                        completion_type="choices",
                        values=sorted(cmd.subcommands.keys()),
                        required=False,
                        description="subcommand",
                    )
                ],
                description=f"Subcommands of {cmd_name}",
            )

    if "help" in commands:
        commands["help"] = CommandCompletion(
            name="help",
            args=[
                CompletionArg(
                    position=1,
                    completion_type="choices",
                    values=all_cmd_names,
                    required=False,
                    description="command",
                )
            ],
            description=commands["help"].description or "Show available commands or detailed help",
            subcommands=help_subcommands,
        )

    if "compgen" in commands:
        commands["compgen"] = CommandCompletion(
            name="compgen",
            args=[
                CompletionArg(
                    position=1,
                    completion_type="choices",
                    values=list(SUPPORTED_SHELLS),
                    required=True,
                    description="shell",
                ),
                CompletionArg(
                    position=2,
                    completion_type="choices",
                    values=["default"],
                    required=False,
                    description="path",
                ),
            ],
            description=commands["compgen"].description or "Generate shell completions",
        )

    if "doc" in commands:
        plugin_names = [p for p in manager.plugins if p != "pyprland"]
        commands["doc"] = CommandCompletion(
            name="doc",
            args=[
                CompletionArg(
                    position=1,
                    completion_type="choices",
                    values=sorted(plugin_names),
                    required=False,
                    description="plugin",
                )
            ],
            description=commands["doc"].description or "Show plugin documentation",
        )


def get_command_completions(manager: Pyprland) -> dict[str, CommandCompletion]:
    """Extract structured completion data from loaded plugins.

    Args:
        manager: The Pyprland manager instance with loaded plugins

    Returns:
        Dict mapping command name -> CommandCompletion (with subcommands for hierarchical commands)
    """
    scratchpad_names: list[str] = list(manager.config.get("scratchpads", {}).keys())
    command_tree = build_command_tree(get_all_commands(manager))

    commands: dict[str, CommandCompletion] = {}
    for root_name, node in command_tree.items():
        commands[root_name] = _build_command_from_node(root_name, node, scratchpad_names)

    _apply_command_overrides(commands, manager)

    return commands
