"""Shell completion generators for pyprland.

Generates dynamic shell completions based on loaded plugins and configuration.
Supports positional argument awareness with type-specific completions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from .command_registry import CommandInfo, build_command_tree, get_all_commands
from .constants import SUPPORTED_SHELLS
from .plugins.wallpapers.models import ColorScheme

if TYPE_CHECKING:
    from collections.abc import Callable

    from .manager import Pyprland

# Default user-level completion paths
DEFAULT_PATHS = {
    "bash": "~/.local/share/bash-completion/completions/pypr",
    "zsh": "~/.zsh/completions/_pypr",
    "fish": "~/.config/fish/completions/pypr.fish",
}

# Commands that use scratchpad names for completion
SCRATCHPAD_COMMANDS = {"toggle", "show", "hide", "attach"}

# Known static completions for specific arg names
KNOWN_COMPLETIONS: dict[str, list[str]] = {
    "scheme": [c.value for c in ColorScheme if c.value] + ["fluorescent"],  # Include alias
    "direction": ["1", "-1"],
}

# Args that should show as hints (no actual completion values)
HINT_ARGS: dict[str, str] = {
    "#RRGGBB": "#RRGGBB (hex color)",
    "color": "#RRGGBB (hex color)",
    "factor": "number (zoom level)",
}


@dataclass
class CompletionArg:
    """Argument completion specification."""

    position: int  # 1-based position after command
    completion_type: str  # "choices", "literal", "hint", "file", "none"
    values: list[str] = field(default_factory=list)  # Values to complete or hint text
    required: bool = True  # Whether the arg is required
    description: str = ""  # Description for zsh


@dataclass
class CommandCompletion:
    """Full completion spec for a command."""

    name: str
    args: list[CompletionArg] = field(default_factory=list)
    description: str = ""
    subcommands: dict[str, CommandCompletion] = field(default_factory=dict)  # For hierarchical commands


def get_default_path(shell: str) -> str:
    """Get the default user-level completion path for a shell.

    Args:
        shell: Shell type ("bash", "zsh", or "fish")

    Returns:
        Expanded absolute path to the default completion file
    """
    return str(Path(DEFAULT_PATHS[shell]).expanduser())


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


def get_command_completions(manager: Pyprland) -> dict[str, CommandCompletion]:
    """Extract structured completion data from loaded plugins.

    Args:
        manager: The Pyprland manager instance with loaded plugins

    Returns:
        Dict mapping command name -> CommandCompletion (with subcommands for hierarchical commands)
    """
    # Get scratchpad names from config for dynamic completion
    scratchpad_names: list[str] = list(manager.config.get("scratchpads", {}).keys())

    all_commands = get_all_commands(manager)
    command_tree = build_command_tree(all_commands)

    def build_completion_args(cmd_name: str, cmd_info: CommandInfo | None) -> list[CompletionArg]:
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

    commands: dict[str, CommandCompletion] = {}

    for root_name, node in command_tree.items():
        # Build subcommands dict
        subcommands: dict[str, CommandCompletion] = {}
        for child_name, child_node in node.children.items():
            if child_node.info:
                subcommands[child_name] = CommandCompletion(
                    name=child_name,
                    args=build_completion_args(child_node.full_name, child_node.info),
                    description=child_node.info.short_description,
                )

        # Build root command completion
        root_args: list[CompletionArg] = []
        root_desc = ""
        if node.info:
            root_args = build_completion_args(root_name, node.info)
            root_desc = node.info.short_description

        commands[root_name] = CommandCompletion(
            name=root_name,
            args=root_args,
            description=root_desc,
            subcommands=subcommands,
        )

    # Override help command with dynamic command list completion
    # Build list of all completable command paths (including subcommands)
    all_cmd_names = sorted(commands.keys())
    # Also build subcommand completions for help
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

    # Override compgen with shell type completion
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

    # Override doc command with plugin list completion
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

    return commands


def _generate_bash_content(commands: dict[str, CommandCompletion]) -> str:
    """Generate bash completion script content.

    Args:
        commands: Dict mapping command name -> CommandCompletion

    Returns:
        The bash completion script content
    """
    cmd_list = " ".join(sorted(commands.keys()))

    # Build case statements for each command
    case_statements: list[str] = []
    for cmd_name, cmd in sorted(commands.items()):
        # Handle commands with subcommands
        if cmd.subcommands:
            subcmd_list = " ".join(sorted(cmd.subcommands.keys()))
            # Position 1 is subcommand selection
            subcmd_cases: list[str] = [f'                1) COMPREPLY=($(compgen -W "{subcmd_list}" -- "$cur"));;']

            # Build per-subcommand argument completions at position 2+
            for subcmd_name, subcmd in sorted(cmd.subcommands.items()):
                for arg in subcmd.args:
                    if arg.completion_type in ("choices", "dynamic", "literal"):
                        values_str = " ".join(arg.values)
                        # Subcommand args start at position 2 (pos 1 is the subcommand itself)
                        subcmd_cases.append(
                            f'                *) [[ "${{COMP_WORDS[2]}}" == "{subcmd_name}" ]] && '
                            f"[[ $pos -eq {arg.position + 1} ]] && "
                            f'COMPREPLY=($(compgen -W "{values_str}" -- "$cur"));;'
                        )

            pos_block = "\n".join(subcmd_cases)
            case_statements.append(f"""            {cmd_name})
                case $pos in
{pos_block}
                esac
                ;;""")
        elif cmd.args:
            # Regular command with args
            pos_cases: list[str] = []
            for arg in cmd.args:
                if arg.completion_type in ("choices", "dynamic", "literal"):
                    values_str = " ".join(arg.values)
                    pos_cases.append(f'                {arg.position}) COMPREPLY=($(compgen -W "{values_str}" -- "$cur"));;')
                elif arg.completion_type == "file":
                    pos_cases.append(f'                {arg.position}) COMPREPLY=($(compgen -f -- "$cur"));;')
                # hint and none types: no completion

            if pos_cases:
                pos_block = "\n".join(pos_cases)
                case_statements.append(f"""            {cmd_name})
                case $pos in
{pos_block}
                esac
                ;;""")

    case_block = "\n".join(case_statements) if case_statements else "            *) ;;"

    return f"""# Bash completion for pypr
# Generated by: pypr compgen bash

_pypr() {{
    local cur="${{COMP_WORDS[COMP_CWORD]}}"
    local cmd="${{COMP_WORDS[1]}}"
    local pos=$((COMP_CWORD - 1))

    if [[ $COMP_CWORD -eq 1 ]]; then
        COMPREPLY=($(compgen -W "{cmd_list}" -- "$cur"))
        return
    fi

    case "$cmd" in
{case_block}
    esac
}}

complete -F _pypr pypr
"""


def _generate_zsh_content(commands: dict[str, CommandCompletion]) -> str:
    """Generate zsh completion script content.

    Args:
        commands: Dict mapping command name -> CommandCompletion

    Returns:
        The zsh completion script content
    """
    # Build command descriptions
    cmd_descs: list[str] = []
    for cmd_name, cmd in sorted(commands.items()):
        desc = cmd.description.replace("'", "'\\''") if cmd.description else cmd_name
        # Add subcommand hint if applicable
        if cmd.subcommands and not cmd.args:
            subcmds = "|".join(sorted(cmd.subcommands.keys()))
            desc = f"<{subcmds}> {desc}" if desc else f"<{subcmds}>"
        cmd_descs.append(f"        '{cmd_name}:{desc}'")
    cmd_desc_block = "\n".join(cmd_descs)

    # Build case statements for each command
    case_statements: list[str] = []
    for cmd_name, cmd in sorted(commands.items()):
        # Handle commands with subcommands
        if cmd.subcommands:
            # Build subcommand descriptions
            subcmd_descs: list[str] = []
            for subcmd_name, subcmd in sorted(cmd.subcommands.items()):
                subdesc = subcmd.description.replace("'", "'\\''") if subcmd.description else subcmd_name
                subcmd_descs.append(f"'{subcmd_name}:{subdesc}'")
            subcmd_desc_str = " ".join(subcmd_descs)

            case_statements.append(f"""                {cmd_name})
                    local -a subcmds=({subcmd_desc_str})
                    if [[ $CURRENT -eq 2 ]]; then
                        _describe 'subcommand' subcmds
                    fi
                    ;;""")
        elif cmd.args:
            # Regular command with args
            arg_specs: list[str] = []
            for arg in cmd.args:
                pos = arg.position
                desc = arg.description.replace("'", "'\\''")

                if arg.completion_type in ("choices", "dynamic", "literal"):
                    values_str = " ".join(arg.values)
                    arg_specs.append(f"'{pos}:{desc}:({values_str})'")
                elif arg.completion_type == "file":
                    arg_specs.append(f"'{pos}:{desc}:_files'")
                elif arg.completion_type == "hint":
                    # Show description but no actual completions
                    hint = arg.values[0] if arg.values else desc
                    arg_specs.append(f"'{pos}:{hint}:'")

            if arg_specs:
                args_line = " \\\n                        ".join(arg_specs)
                case_statements.append(f"""                {cmd_name})
                    _arguments \\
                        {args_line}
                    ;;""")

    case_block = "\n".join(case_statements) if case_statements else "                *) ;;"

    return f"""#compdef pypr
# Zsh completion for pypr
# Generated by: pypr compgen zsh

_pypr() {{
    local -a commands=(
{cmd_desc_block}
    )

    _arguments -C \\
        '1:command:->command' \\
        '*::arg:->args'

    case $state in
        command)
            _describe 'command' commands
            ;;
        args)
            case $words[1] in
{case_block}
            esac
            ;;
    esac
}}

_pypr "$@"
"""


def _generate_fish_content(commands: dict[str, CommandCompletion]) -> str:
    """Generate fish completion script content.

    Args:
        commands: Dict mapping command name -> CommandCompletion

    Returns:
        The fish completion script content
    """
    lines = [
        "# Fish completion for pypr",
        "# Generated by: pypr compgen fish",
        "",
        "# Disable default file completions for pypr",
        "complete -c pypr -f",
        "",
        "# Helper function to count args after command",
        "function __pypr_arg_count",
        "    set -l cmd (commandline -opc)",
        "    math (count $cmd) - 1",
        "end",
        "",
        "# Main commands",
    ]

    # Add main command completions
    for cmd_name, cmd in sorted(commands.items()):
        desc = cmd.description.replace('"', '\\"') if cmd.description else ""
        # Add subcommand hint if applicable
        if cmd.subcommands and not cmd.args and not desc:
            subcmds = "|".join(sorted(cmd.subcommands.keys()))
            desc = f"<{subcmds}>"
        if desc:
            lines.append(f'complete -c pypr -n "__fish_use_subcommand" -a "{cmd_name}" -d "{desc}"')
        else:
            lines.append(f'complete -c pypr -n "__fish_use_subcommand" -a "{cmd_name}"')

    lines.append("")
    lines.append("# Subcommand and positional argument completions")

    for cmd_name, cmd in sorted(commands.items()):
        # Handle commands with subcommands
        if cmd.subcommands:
            for subcmd_name, subcmd in sorted(cmd.subcommands.items()):
                subdesc = subcmd.description.replace('"', '\\"') if subcmd.description else ""
                if subdesc:
                    lines.append(
                        f'complete -c pypr -n "__fish_seen_subcommand_from {cmd_name}; '
                        f'and test (__pypr_arg_count) -eq 1" -a "{subcmd_name}" -d "{subdesc}"'
                    )
                else:
                    lines.append(
                        f'complete -c pypr -n "__fish_seen_subcommand_from {cmd_name}; '
                        f'and test (__pypr_arg_count) -eq 1" -a "{subcmd_name}"'
                    )
        elif cmd.args:
            # Regular command with args
            for arg in cmd.args:
                if arg.completion_type in ("choices", "dynamic", "literal"):
                    values_str = " ".join(arg.values)
                    lines.append(
                        f'complete -c pypr -n "__fish_seen_subcommand_from {cmd_name}; '
                        f'and test (__pypr_arg_count) -eq {arg.position}" -a "{values_str}"'
                    )
                elif arg.completion_type == "file":
                    # Enable file completion for this position
                    lines.append(
                        f'complete -c pypr -n "__fish_seen_subcommand_from {cmd_name}; and test (__pypr_arg_count) -eq {arg.position}" -F'
                    )
                # hint type: no completion added

    return "\n".join(lines) + "\n"


GENERATORS: dict[str, Callable[[dict[str, CommandCompletion]], str]] = {
    "bash": _generate_bash_content,
    "zsh": _generate_zsh_content,
    "fish": _generate_fish_content,
}


def _get_success_message(shell: str, output_path: str, used_default: bool) -> str:
    """Generate a friendly success message after installing completions.

    Args:
        shell: Shell type
        output_path: Path where completions were written
        used_default: Whether the default path was used

    Returns:
        User-friendly success message
    """
    # Use ~ in display path for readability
    display_path = output_path.replace(str(Path.home()), "~")

    if not used_default:
        return f"Completions written to {display_path}"

    if shell == "bash":
        return f"Completions installed to {display_path}\nReload your shell or run: source ~/.bashrc"

    if shell == "zsh":
        return (
            f"Completions installed to {display_path}\n"
            "Ensure ~/.zsh/completions is in your fpath. Add to ~/.zshrc:\n"
            "  fpath=(~/.zsh/completions $fpath)\n"
            "  autoload -Uz compinit && compinit\n"
            "Then reload your shell."
        )

    if shell == "fish":
        return f"Completions installed to {display_path}\nReload your shell or run: source ~/.config/fish/config.fish"

    return f"Completions written to {display_path}"


def _parse_compgen_args(args: str) -> tuple[bool, str, str | None]:
    """Parse and validate compgen command arguments.

    Args:
        args: Arguments after "compgen" (e.g., "zsh" or "zsh default")

    Returns:
        Tuple of (success, shell_or_error, path_arg):
        - On success: (True, shell, path_arg or None)
        - On failure: (False, error_message, None)
    """
    parts = args.split(None, 1)
    if not parts:
        shells = "|".join(SUPPORTED_SHELLS)
        return (False, f"Usage: compgen <{shells}> [default|path]", None)

    shell = parts[0]
    if shell not in SUPPORTED_SHELLS:
        return (False, f"Unsupported shell: {shell}. Supported: {', '.join(SUPPORTED_SHELLS)}", None)

    path_arg = parts[1] if len(parts) > 1 else None
    if path_arg is not None and path_arg != "default" and not path_arg.startswith(("/", "~")):
        return (False, "Relative paths not supported. Use absolute path, ~/path, or 'default'.", None)

    return (True, shell, path_arg)


def handle_compgen(manager: Pyprland, args: str) -> tuple[bool, str]:
    """Handle compgen command with path semantics.

    Args:
        manager: The Pyprland manager instance
        args: Arguments after "compgen" (e.g., "zsh" or "zsh default")

    Returns:
        Tuple of (success, result):
        - No path arg: result is the script content
        - With path arg: result is success/error message
    """
    success, shell_or_error, path_arg = _parse_compgen_args(args)
    if not success:
        return (False, shell_or_error)

    shell = shell_or_error

    try:
        commands = get_command_completions(manager)
        content = GENERATORS[shell](commands)
    except (KeyError, ValueError, TypeError) as e:
        return (False, f"Failed to generate completions: {e}")

    if path_arg is None:
        return (True, content)

    # Determine output path
    if path_arg == "default":
        output_path = get_default_path(shell)
        used_default = True
    else:
        output_path = str(Path(path_arg).expanduser())
        used_default = False

    manager.log.debug("Writing completions to: %s", output_path)

    # Write to file
    try:
        parent_dir = Path(output_path).parent
        parent_dir.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(content, encoding="utf-8")
    except OSError as e:
        return (False, f"Failed to write completion file: {e}")

    return (True, _get_success_message(shell, output_path, used_default))
