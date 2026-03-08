"""Tests for command registry."""

import pytest

from pyprland.commands.discovery import extract_commands_from_object, get_client_commands
from pyprland.commands.models import CommandArg, CommandInfo
from pyprland.commands.parsing import parse_docstring
from pyprland.commands.tree import build_command_tree, get_display_name, get_parent_prefixes


class TestParseDocstring:
    """Tests for parse_docstring function."""

    def test_required_arg(self):
        """Test parsing a required argument."""
        args, short, full = parse_docstring("<name> Toggle a scratchpad")
        assert len(args) == 1
        assert args[0].value == "name"
        assert args[0].required is True
        assert short == "Toggle a scratchpad"
        assert full == "<name> Toggle a scratchpad"

    def test_optional_arg(self):
        """Test parsing an optional argument."""
        args, short, full = parse_docstring("[command] Show help")
        assert len(args) == 1
        assert args[0].value == "command"
        assert args[0].required is False
        assert short == "Show help"

    def test_mixed_args(self):
        """Test parsing mixed required and optional arguments."""
        args, short, full = parse_docstring("<shell> [path] Generate completions")
        assert len(args) == 2
        assert args[0].value == "shell"
        assert args[0].required is True
        assert args[1].value == "path"
        assert args[1].required is False
        assert short == "Generate completions"

    def test_no_args(self):
        """Test parsing docstring with no arguments."""
        args, short, full = parse_docstring("Show the version")
        assert args == []
        assert short == "Show the version"
        assert full == "Show the version"

    def test_pipe_choices(self):
        """Test parsing argument with pipe-separated choices."""
        args, short, _ = parse_docstring("<next|prev|clear> Control playback")
        assert len(args) == 1
        assert args[0].value == "next|prev|clear"
        assert args[0].required is True
        assert short == "Control playback"

    def test_empty_docstring(self):
        """Test parsing empty docstring."""
        args, short, full = parse_docstring("")
        assert args == []
        assert short == "No description available."
        assert full == ""

    def test_multiline_docstring(self):
        """Test parsing multiline docstring."""
        doc = """<arg> Short description.

        Detailed explanation here.
        More details."""
        args, short, full = parse_docstring(doc)
        assert len(args) == 1
        assert args[0].value == "arg"
        assert short == "Short description."
        assert "Detailed explanation" in full

    def test_arg_only_no_description(self):
        """Test docstring with only an argument, no description."""
        args, short, full = parse_docstring("<name>")
        assert len(args) == 1
        assert args[0].value == "name"
        assert short == "<name>"  # Falls back to full first line

    def test_multiple_optional_args(self):
        """Test parsing multiple optional arguments."""
        args, short, _ = parse_docstring("[arg1] [arg2] [arg3] Do something")
        assert len(args) == 3
        assert all(not arg.required for arg in args)
        assert short == "Do something"


class TestExtractCommandsFromObject:
    """Tests for extract_commands_from_object function."""

    def test_extract_from_class(self):
        """Test extracting commands from a class."""

        class FakePlugin:
            def run_test(self):
                """Do a test."""

            def run_other(self, arg):
                """<arg> Other command."""

            def not_a_command(self):
                """This is not a command."""

        cmds = extract_commands_from_object(FakePlugin, source="fake")
        assert len(cmds) == 2
        names = {c.name for c in cmds}
        assert names == {"test", "other"}

    def test_extract_from_instance(self):
        """Test extracting commands from an instance."""

        class FakePlugin:
            def run_hello(self):
                """Say hello."""

        instance = FakePlugin()
        cmds = extract_commands_from_object(instance, source="test")
        assert len(cmds) == 1
        assert cmds[0].name == "hello"
        assert cmds[0].short_description == "Say hello."

    def test_source_preserved(self):
        """Test that source is correctly preserved."""

        class FakePlugin:
            def run_cmd(self):
                """A command."""

        cmds = extract_commands_from_object(FakePlugin, source="myplugin")
        assert cmds[0].source == "myplugin"

    def test_args_extracted(self):
        """Test that arguments are correctly extracted."""

        class FakePlugin:
            def run_toggle(self, name):
                """<name> Toggle something."""

        cmds = extract_commands_from_object(FakePlugin, source="test")
        assert len(cmds[0].args) == 1
        assert cmds[0].args[0].value == "name"
        assert cmds[0].args[0].required is True

    def test_no_commands(self):
        """Test class with no run_ methods."""

        class EmptyPlugin:
            def do_something(self):
                """Not a command."""

        cmds = extract_commands_from_object(EmptyPlugin, source="empty")
        assert cmds == []

    def test_method_without_docstring(self):
        """Test method without docstring."""

        class FakePlugin:
            def run_nodoc(self):
                pass

        cmds = extract_commands_from_object(FakePlugin, source="test")
        assert len(cmds) == 1
        assert cmds[0].short_description == "No description available."


class TestGetClientCommands:
    """Tests for get_client_commands function."""

    def test_returns_edit_and_validate(self):
        """Test that edit and validate commands are returned."""
        cmds = get_client_commands()
        names = {c.name for c in cmds}
        assert "edit" in names
        assert "validate" in names

    def test_source_is_client(self):
        """Test that source is set to 'client'."""
        cmds = get_client_commands()
        for cmd in cmds:
            assert cmd.source == "client"

    def test_has_descriptions(self):
        """Test that client commands have descriptions."""
        cmds = get_client_commands()
        for cmd in cmds:
            assert cmd.short_description
            assert cmd.full_description


class TestCommandInfoDataclass:
    """Tests for CommandInfo dataclass."""

    def test_create_command_info(self):
        """Test creating a CommandInfo instance."""
        cmd = CommandInfo(
            name="test",
            args=[CommandArg(value="arg1", required=True)],
            short_description="Short",
            full_description="Full description",
            source="plugin",
        )
        assert cmd.name == "test"
        assert len(cmd.args) == 1
        assert cmd.source == "plugin"


class TestCommandArgDataclass:
    """Tests for CommandArg dataclass."""

    def test_create_required_arg(self):
        """Test creating a required argument."""
        arg = CommandArg(value="name", required=True)
        assert arg.value == "name"
        assert arg.required is True

    def test_create_optional_arg(self):
        """Test creating an optional argument."""
        arg = CommandArg(value="option", required=False)
        assert arg.value == "option"
        assert arg.required is False


def _make_cmd(name: str, source: str) -> CommandInfo:
    """Helper to create a minimal CommandInfo for tree tests."""
    return CommandInfo(
        name=name,
        args=[],
        short_description=f"{name} command",
        full_description=f"{name} command",
        source=source,
    )


class TestGetParentPrefixes:
    """Tests for get_parent_prefixes function."""

    def test_same_source_groups(self):
        """Commands from the same source sharing a prefix are grouped."""
        commands = {
            "wall_next": "wallpapers",
            "wall_pause": "wallpapers",
            "wall_clear": "wallpapers",
        }
        prefixes = get_parent_prefixes(commands)
        assert "wall" in prefixes

    def test_different_sources_not_grouped(self):
        """Commands from different sources sharing a prefix are NOT grouped."""
        commands = {
            "toggle": "scratchpads",
            "toggle_dpms": "toggle_dpms",
            "toggle_special": "toggle_special",
        }
        prefixes = get_parent_prefixes(commands)
        assert "toggle" not in prefixes

    def test_mixed_same_and_different_sources(self):
        """Only same-source prefixes are grouped; cross-plugin ones are not."""
        commands = {
            "wall_next": "wallpapers",
            "wall_pause": "wallpapers",
            "toggle": "scratchpads",
            "toggle_dpms": "toggle_dpms",
        }
        prefixes = get_parent_prefixes(commands)
        assert "wall" in prefixes
        assert "toggle" not in prefixes

    def test_single_command_no_grouping(self):
        """A lone command with underscores does not create a parent prefix."""
        commands = {
            "layout_center": "layout_center",
        }
        prefixes = get_parent_prefixes(commands)
        assert "layout" not in prefixes

    def test_legacy_iterable_groups_all(self):
        """Legacy iterable input (no source info) groups by prefix count only."""
        commands = ["toggle_dpms", "toggle_special"]
        prefixes = get_parent_prefixes(commands)
        # Without source info, both share empty source, so "toggle" is grouped
        assert "toggle" in prefixes


class TestBuildCommandTree:
    """Tests for build_command_tree function."""

    def test_cross_plugin_commands_stay_flat(self):
        """Commands from different plugins with shared prefix remain separate root entries."""
        commands = {
            "toggle": _make_cmd("toggle", "scratchpads"),
            "toggle_dpms": _make_cmd("toggle_dpms", "toggle_dpms"),
            "toggle_special": _make_cmd("toggle_special", "toggle_special"),
        }
        tree = build_command_tree(commands)

        # Each command should be its own root node, not nested
        assert "toggle" in tree
        assert "toggle_dpms" in tree
        assert "toggle_special" in tree

        # toggle should have no children
        assert tree["toggle"].children == {}
        assert tree["toggle_dpms"].children == {}
        assert tree["toggle_special"].children == {}

    def test_same_plugin_commands_grouped(self):
        """Commands from the same plugin with shared prefix are grouped."""
        commands = {
            "wall_next": _make_cmd("wall_next", "wallpapers"),
            "wall_pause": _make_cmd("wall_pause", "wallpapers"),
            "wall_clear": _make_cmd("wall_clear", "wallpapers"),
        }
        tree = build_command_tree(commands)

        # Should have a single root "wall" with children
        assert "wall" in tree
        assert "wall_next" not in tree
        assert "wall_pause" not in tree
        assert "wall_clear" not in tree

        wall = tree["wall"]
        assert "next" in wall.children
        assert "pause" in wall.children
        assert "clear" in wall.children

    def test_mixed_plugins_correct_grouping(self):
        """Same-plugin commands group while cross-plugin ones stay flat."""
        commands = {
            "wall_next": _make_cmd("wall_next", "wallpapers"),
            "wall_pause": _make_cmd("wall_pause", "wallpapers"),
            "toggle": _make_cmd("toggle", "scratchpads"),
            "toggle_dpms": _make_cmd("toggle_dpms", "toggle_dpms"),
        }
        tree = build_command_tree(commands)

        # wall commands grouped
        assert "wall" in tree
        assert "next" in tree["wall"].children
        assert "pause" in tree["wall"].children

        # toggle commands NOT grouped
        assert "toggle" in tree
        assert "toggle_dpms" in tree
        assert tree["toggle"].children == {}

    def test_root_command_with_same_source_children(self):
        """A root command that is also a prefix keeps its info and gets children."""
        commands = {
            "wall": _make_cmd("wall", "wallpapers"),
            "wall_next": _make_cmd("wall_next", "wallpapers"),
            "wall_pause": _make_cmd("wall_pause", "wallpapers"),
        }
        tree = build_command_tree(commands)

        assert "wall" in tree
        wall = tree["wall"]
        assert wall.info is not None
        assert wall.info.source == "wallpapers"
        assert "next" in wall.children
        assert "pause" in wall.children


class TestGetDisplayName:
    """Tests for get_display_name function."""

    def test_hierarchical_command(self):
        """Hierarchical command gets space-separated display name."""
        parent_prefixes = {"wall"}
        assert get_display_name("wall_next", parent_prefixes) == "wall next"

    def test_non_hierarchical_command(self):
        """Non-hierarchical command keeps underscore name."""
        parent_prefixes = {"wall"}
        assert get_display_name("toggle_dpms", parent_prefixes) == "toggle_dpms"

    def test_no_parent_prefixes(self):
        """With no parent prefixes, all commands keep underscore names."""
        parent_prefixes: set[str] = set()
        assert get_display_name("toggle_dpms", parent_prefixes) == "toggle_dpms"
        assert get_display_name("wall_next", parent_prefixes) == "wall_next"
