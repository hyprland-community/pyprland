"""Tests for shell completion generators.

Tests use the generated JSON files from site/generated/ as source of truth
and validate completion scripts with real shells when available.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from pyprland.commands.models import CommandArg, CommandInfo
from pyprland.commands.tree import build_command_tree
from pyprland.completions.discovery import _build_command_from_node, _classify_arg
from pyprland.completions.generators.bash import generate_bash
from pyprland.completions.generators.fish import generate_fish
from pyprland.completions.generators.zsh import generate_zsh
from pyprland.completions.models import CommandCompletion, CompletionArg

GENERATED_DIR = Path(__file__).parent.parent / "site" / "generated"


def _load_commands_from_json() -> dict[str, CommandInfo]:
    """Load all commands from generated JSON files into CommandInfo objects."""
    commands: dict[str, CommandInfo] = {}

    for json_file in GENERATED_DIR.glob("*.json"):
        if json_file.stem in ("index", "generted_files"):
            continue

        data = json.loads(json_file.read_text())
        plugin_name = data["name"]

        for cmd in data.get("commands", []):
            args = [CommandArg(value=arg["value"], required=arg["required"]) for arg in cmd.get("args", [])]
            commands[cmd["name"]] = CommandInfo(
                name=cmd["name"],
                args=args,
                short_description=cmd.get("short_description", ""),
                full_description=cmd.get("full_description", ""),
                source=plugin_name,
            )

    return commands


def _build_completions_from_json() -> dict[str, CommandCompletion]:
    """Build CommandCompletion objects from generated JSON files."""
    all_commands = _load_commands_from_json()
    command_tree = build_command_tree(all_commands)

    # Build completions from tree (simplified, no scratchpad names)
    completions: dict[str, CommandCompletion] = {}
    for root_name, node in command_tree.items():
        completions[root_name] = _build_command_from_node(root_name, node, [])

    # Apply help command override (simplified version)
    all_cmd_names = sorted(completions.keys())
    help_subcommands: dict[str, CommandCompletion] = {}
    for cmd_name, cmd in completions.items():
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

    if "help" in completions:
        completions["help"] = CommandCompletion(
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
            description="Show available commands or detailed help",
            subcommands=help_subcommands,
        )

    return completions


@pytest.fixture(scope="module")
def commands_from_json() -> dict[str, CommandCompletion]:
    """Build CommandCompletion objects from generated JSON files."""
    return _build_completions_from_json()


@pytest.fixture(scope="module")
def zsh_script(commands_from_json: dict[str, CommandCompletion]) -> str:
    """Generate zsh completion script."""
    return generate_zsh(commands_from_json)


@pytest.fixture(scope="module")
def bash_script(commands_from_json: dict[str, CommandCompletion]) -> str:
    """Generate bash completion script."""
    return generate_bash(commands_from_json)


@pytest.fixture(scope="module")
def fish_script(commands_from_json: dict[str, CommandCompletion]) -> str:
    """Generate fish completion script."""
    return generate_fish(commands_from_json)


# --- Syntax validation with real shells ---


@pytest.mark.skipif(not shutil.which("zsh"), reason="zsh not installed")
class TestZshSyntax:
    """Test zsh completion script syntax."""

    def test_syntax_valid(self, zsh_script: str) -> None:
        """Zsh completion script should have valid syntax."""
        result = subprocess.run(
            ["zsh", "-n", "-c", zsh_script],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Zsh syntax error: {result.stderr}"


@pytest.mark.skipif(not shutil.which("bash"), reason="bash not installed")
class TestBashSyntax:
    """Test bash completion script syntax."""

    def test_syntax_valid(self, bash_script: str) -> None:
        """Bash completion script should have valid syntax."""
        result = subprocess.run(
            ["bash", "-n", "-c", bash_script],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Bash syntax error: {result.stderr}"


@pytest.mark.skipif(not shutil.which("fish"), reason="fish not installed")
class TestFishSyntax:
    """Test fish completion script syntax."""

    def test_syntax_valid(self, fish_script: str, tmp_path: Path) -> None:
        """Fish completion script should have valid syntax."""
        script_file = tmp_path / "completions.fish"
        script_file.write_text(fish_script)
        result = subprocess.run(
            ["fish", "--no-execute", str(script_file)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Fish syntax error: {result.stderr}"


# --- Command presence tests ---


class TestZshCommandPresence:
    """Test that all commands appear in zsh completion."""

    def test_all_commands_present(self, zsh_script: str, commands_from_json: dict[str, CommandCompletion]) -> None:
        """All commands should appear in zsh completion."""
        for cmd_name in commands_from_json:
            assert cmd_name in zsh_script, f"Command '{cmd_name}' missing from zsh"

    def test_help_case_exists(self, zsh_script: str) -> None:
        """Help command should have a case statement."""
        assert "help)" in zsh_script

    def test_help_uses_commands_array(self, zsh_script: str) -> None:
        """Help command should use the commands array for completion."""
        assert "_describe 'command' commands" in zsh_script


class TestBashCommandPresence:
    """Test that all commands appear in bash completion."""

    def test_all_commands_present(self, bash_script: str, commands_from_json: dict[str, CommandCompletion]) -> None:
        """All commands should appear in bash completion."""
        for cmd_name in commands_from_json:
            assert cmd_name in bash_script, f"Command '{cmd_name}' missing from bash"

    def test_help_case_exists(self, bash_script: str) -> None:
        """Help command should have a case statement."""
        assert "help)" in bash_script


class TestFishCommandPresence:
    """Test that all commands appear in fish completion."""

    def test_all_commands_present(self, fish_script: str, commands_from_json: dict[str, CommandCompletion]) -> None:
        """All commands should appear in fish completion."""
        for cmd_name in commands_from_json:
            assert cmd_name in fish_script, f"Command '{cmd_name}' missing from fish"

    def test_help_completion_exists(self, fish_script: str) -> None:
        """Help command should have completion rules."""
        assert "__fish_seen_subcommand_from help" in fish_script


# --- Subcommand tests ---


class TestSubcommandCompletions:
    """Test that subcommands are properly handled."""

    def test_zsh_wall_subcommands(self, zsh_script: str) -> None:
        """Wall subcommands should appear in zsh completion."""
        assert "wall)" in zsh_script
        # Check for at least some known subcommands
        for subcmd in ["next", "pause", "clear"]:
            assert subcmd in zsh_script, f"Wall subcommand '{subcmd}' missing"

    def test_bash_wall_subcommands(self, bash_script: str) -> None:
        """Wall subcommands should appear in bash completion."""
        assert "wall)" in bash_script
        for subcmd in ["next", "pause", "clear"]:
            assert subcmd in bash_script, f"Wall subcommand '{subcmd}' missing"

    def test_fish_wall_subcommands(self, fish_script: str) -> None:
        """Wall subcommands should appear in fish completion."""
        for subcmd in ["next", "pause", "clear"]:
            assert subcmd in fish_script, f"Wall subcommand '{subcmd}' missing"

    def test_zsh_help_wall_subcommands(self, zsh_script: str) -> None:
        """Help wall should complete with wall's subcommands."""
        # The help case should have a nested case for wall
        assert "wall) compadd" in zsh_script or ("wall)" in zsh_script and "compadd" in zsh_script)

    def test_bash_help_wall_subcommands(self, bash_script: str) -> None:
        """Help wall should complete with wall's subcommands."""
        # Check that help case handles wall subcommands
        assert "COMP_WORDS[2]" in bash_script  # Used for subcommand detection

    def test_fish_help_wall_subcommands(self, fish_script: str) -> None:
        """Help wall should complete with wall's subcommands."""
        assert "contains wall" in fish_script
