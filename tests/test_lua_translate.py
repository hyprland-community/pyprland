"""Tests for pyprland.adapters.lua_translate module.

Validates that generated Lua code is both correct (string assertions)
and syntactically valid (luac -p parsing).
"""

from __future__ import annotations

import subprocess

import pytest

from pyprland.adapters.lua_translate import dispatch_to_lua_call, keyword_to_lua_code


def validate_lua(code: str) -> None:
    """Assert that code is syntactically valid Lua via luac -p."""
    result = subprocess.run(
        ["luac", "-p", "-"],
        input=code.encode(),
        capture_output=True,
    )
    assert result.returncode == 0, f"Invalid Lua syntax:\n  code: {code}\n  error: {result.stderr.decode().strip()}"


# --- Keyword translation tests ---


class TestKeywordToLua:
    """Tests for keyword_to_lua_code()."""

    @pytest.mark.parametrize(
        ("cmd", "expected"),
        [
            # Config: numeric value
            (
                "general:border_size 5",
                "hl.config({general={border_size=5}})",
            ),
            # Config: boolean value (key ends with "enabled")
            (
                "misc:enabled true",
                "hl.config({misc={enabled=true}})",
            ),
            (
                "misc:enabled false",
                "hl.config({misc={enabled=false}})",
            ),
            # Config: string value
            (
                "general:col:active_border rgba(33ccffee)",
                'hl.config({general={col={active_border="rgba(33ccffee)"}}})',
            ),
            # Config: deeply nested
            (
                "input:touchpad:natural_scroll 1",
                "hl.config({input={touchpad={natural_scroll=1}}})",
            ),
            # Config: float number
            (
                "general:gaps_out 0.5",
                "hl.config({general={gaps_out=0.5}})",
            ),
        ],
        ids=[
            "config-numeric",
            "config-bool-true",
            "config-bool-false",
            "config-string",
            "config-deeply-nested",
            "config-float",
        ],
    )
    def test_config_keywords(self, cmd: str, expected: str) -> None:
        result = keyword_to_lua_code(cmd)
        assert result == expected
        validate_lua(result)

    @pytest.mark.parametrize(
        ("cmd", "expected"),
        [
            # Named: enable
            (
                "windowrule[myrule]:enable true",
                'hl.window_rule({name="myrule", enabled=true})',
            ),
            (
                "windowrule[myrule]:enable false",
                'hl.window_rule({name="myrule", enabled=false})',
            ),
            # Named: match
            (
                "windowrule[myrule]:match:class kitty",
                'hl.window_rule({name="myrule", match={class="kitty"}})',
            ),
            # Named: bool effect (no value)
            (
                "windowrule[myrule]:float",
                'hl.window_rule({name="myrule", float=true})',
            ),
            # Named: bool effect with explicit value
            (
                "windowrule[myrule]:float true",
                'hl.window_rule({name="myrule", float=true})',
            ),
            # Named: string effect
            (
                "windowrule[myrule]:opacity 0.8",
                'hl.window_rule({name="myrule", opacity=0.8})',
            ),
        ],
        ids=[
            "named-enable-true",
            "named-enable-false",
            "named-match-class",
            "named-bool-no-value",
            "named-bool-with-value",
            "named-string-effect",
        ],
    )
    def test_named_window_rules(self, cmd: str, expected: str) -> None:
        result = keyword_to_lua_code(cmd)
        assert result == expected
        validate_lua(result)

    @pytest.mark.parametrize(
        ("cmd", "expected"),
        [
            # Anonymous: effect only
            (
                "windowrule float",
                "hl.window_rule({float=true})",
            ),
            # Anonymous: effect with match (class: shorthand)
            (
                "windowrule float, class:kitty",
                'hl.window_rule({float=true, match={class="kitty"}})',
            ),
            # Anonymous: effect with match: prefix
            (
                "windowrule pin, match:title Firefox",
                'hl.window_rule({pin=true, match={title="Firefox"}})',
            ),
            # Anonymous: non-bool effect with match
            (
                "windowrule opacity 0.9, class:Alacritty",
                'hl.window_rule({opacity=0.9, match={class="Alacritty"}})',
            ),
            # Anonymous: numeric effect with match (tag)
            (
                "windowrule border_size 3, match:tag layout_center",
                'hl.window_rule({border_size=3, match={tag="layout_center"}})',
            ),
        ],
        ids=[
            "anon-effect-only",
            "anon-with-class-match",
            "anon-with-match-prefix",
            "anon-string-effect-with-match",
            "anon-numeric-effect-with-tag",
        ],
    )
    def test_anonymous_window_rules(self, cmd: str, expected: str) -> None:
        result = keyword_to_lua_code(cmd)
        assert result == expected
        validate_lua(result)

    @pytest.mark.parametrize(
        ("cmd", "expected"),
        [
            # Workspace: name only
            (
                "workspace special",
                'hl.workspace_rule({workspace="special"})',
            ),
            # Workspace: name with options
            (
                "workspace 1, persistent:true, default:true",
                'hl.workspace_rule({workspace="1", persistent=true, default=true})',
            ),
            # Workspace: option with string value
            (
                "workspace 2, monitor:HDMI-A-1",
                'hl.workspace_rule({workspace="2", monitor="HDMI-A-1"})',
            ),
        ],
        ids=[
            "workspace-name-only",
            "workspace-with-bool-opts",
            "workspace-with-string-opt",
        ],
    )
    def test_workspace_rules(self, cmd: str, expected: str) -> None:
        result = keyword_to_lua_code(cmd)
        assert result == expected
        validate_lua(result)

    @pytest.mark.parametrize(
        ("cmd", "expected"),
        [
            (
                "monitor HDMI-A-1,disable",
                'hl.monitor({output="HDMI-A-1", disabled=true})',
            ),
            (
                "monitor DP-1,1920x1080@60,0x0,1.0,transform,0",
                'hl.monitor({output="DP-1", mode="1920x1080@60", position="0x0", scale=1.0, transform=0})',
            ),
            (
                "monitor HDMI-A-1,3440x1440@59.999,1920x0,2.0,transform,1",
                'hl.monitor({output="HDMI-A-1", mode="3440x1440@59.999", position="1920x0", scale=2.0, transform=1})',
            ),
            (
                "monitor eDP-1,1920x1080@60,0x0,1.5",
                'hl.monitor({output="eDP-1", mode="1920x1080@60", position="0x0", scale=1.5})',
            ),
        ],
        ids=["monitor-disable", "monitor-full", "monitor-full-transform", "monitor-no-transform"],
    )
    def test_monitor(self, cmd: str, expected: str) -> None:
        result = keyword_to_lua_code(cmd)
        assert result == expected
        validate_lua(result)

    def test_monitor_unknown_action_returns_none(self) -> None:
        # Incomplete monitor commands aren't translated
        assert keyword_to_lua_code("monitor HDMI-A-1,1920x1080@60") is None

    def test_unknown_keyword_returns_none(self) -> None:
        assert keyword_to_lua_code("exec-once waybar") is None

    def test_no_colon_no_prefix_returns_none(self) -> None:
        assert keyword_to_lua_code("something without colon") is None


# --- Dispatch translation tests ---


class TestDispatchToLua:
    """Tests for dispatch_to_lua_call()."""

    @pytest.mark.parametrize(
        ("cmd", "expected"),
        [
            # movetoworkspacesilent
            (
                "movetoworkspacesilent 3",
                'hl.dsp.window.move({workspace="3", follow=false})',
            ),
            (
                "movetoworkspacesilent 3,address:0xabc",
                'hl.dsp.window.move({workspace="3", follow=false, window="address:0xabc"})',
            ),
            # movetoworkspace
            (
                "movetoworkspace 2",
                'hl.dsp.window.move({workspace="2"})',
            ),
            (
                "movetoworkspace special,title:foo",
                'hl.dsp.window.move({workspace="special", window="title:foo"})',
            ),
            # movewindowpixel (exact)
            (
                "movewindowpixel exact 100 200,address:0x1",
                'hl.dsp.window.move({x=100, y=200, window="address:0x1"})',
            ),
            # resizewindowpixel (exact)
            (
                "resizewindowpixel exact 800 600,address:0x2",
                'hl.dsp.window.resize({x=800, y=600, window="address:0x2"})',
            ),
            # tagwindow
            (
                "tagwindow mytag",
                'hl.dsp.window.tag({tag="mytag"})',
            ),
            (
                "tagwindow mytag address:0x3",
                'hl.dsp.window.tag({tag="mytag", window="address:0x3"})',
            ),
            # focuswindow
            (
                "focuswindow address:0x4",
                'hl.dsp.focus({window="address:0x4"})',
            ),
            # pin
            (
                "pin ",
                "hl.dsp.window.pin({})",
            ),
            (
                "pin address:0x5",
                'hl.dsp.window.pin({window="address:0x5"})',
            ),
            # togglefloating
            (
                "togglefloating ",
                "hl.dsp.window.float({})",
            ),
            (
                "togglefloating address:0x6",
                'hl.dsp.window.float({window="address:0x6"})',
            ),
            # closewindow
            (
                "closewindow address:0x7",
                'hl.dsp.window.close({window="address:0x7"})',
            ),
            # alterzorder
            (
                "alterzorder top,address:0x8",
                'hl.dsp.window.alter_zorder({mode="top", window="address:0x8"})',
            ),
            # moveworkspacetomonitor
            (
                "moveworkspacetomonitor 1 HDMI-A-1",
                'hl.dsp.workspace.move({id="1", monitor="HDMI-A-1"})',
            ),
            # swapactiveworkspaces
            (
                "swapactiveworkspaces eDP-1 HDMI-A-1",
                'hl.dsp.workspace.swap_monitors({monitor1="eDP-1", monitor2="HDMI-A-1"})',
            ),
            # togglespecialworkspace
            (
                "togglespecialworkspace scratchpad",
                'hl.dsp.workspace.toggle_special("scratchpad")',
            ),
            (
                "togglespecialworkspace ",
                'hl.dsp.workspace.toggle_special("")',
            ),
            # dpms
            (
                "dpms off",
                'hl.dsp.dpms({action="off"})',
            ),
            (
                "dpms on HDMI-A-1",
                'hl.dsp.dpms({action="on", monitor="HDMI-A-1"})',
            ),
            # execr
            (
                "execr notify-send hello",
                'hl.dsp.exec_raw("notify-send hello")',
            ),
            # exec
            (
                "exec kitty",
                'hl.dsp.exec_cmd("kitty")',
            ),
        ],
        ids=[
            "movetoworkspacesilent-simple",
            "movetoworkspacesilent-with-window",
            "movetoworkspace-simple",
            "movetoworkspace-with-window",
            "movewindowpixel-exact",
            "resizewindowpixel-exact",
            "tagwindow-no-window",
            "tagwindow-with-window",
            "focuswindow",
            "pin-no-arg",
            "pin-with-window",
            "togglefloating-no-arg",
            "togglefloating-with-window",
            "closewindow",
            "alterzorder",
            "moveworkspacetomonitor",
            "swapactiveworkspaces",
            "togglespecialworkspace-named",
            "togglespecialworkspace-empty",
            "dpms-off",
            "dpms-on-monitor",
            "execr",
            "exec",
        ],
    )
    def test_dispatch(self, cmd: str, expected: str) -> None:
        result = dispatch_to_lua_call(cmd)
        assert result == expected
        validate_lua(result)

    def test_unknown_dispatch_returns_none(self) -> None:
        assert dispatch_to_lua_call("nonexistent arg1 arg2") is None

    def test_movewindowpixel_non_exact_returns_none(self) -> None:
        assert dispatch_to_lua_call("movewindowpixel 10 20,address:0x1") is None

    def test_resizewindowpixel_non_exact_returns_none(self) -> None:
        assert dispatch_to_lua_call("resizewindowpixel 10 20,address:0x1") is None

    def test_alterzorder_no_comma_returns_none(self) -> None:
        assert dispatch_to_lua_call("alterzorder top") is None


# --- Special character escaping ---


class TestEscaping:
    """Ensure special characters in values produce valid Lua strings."""

    def test_backslash_in_value(self) -> None:
        result = keyword_to_lua_code("general:col 1\\2")
        assert result is not None
        assert "1\\\\2" in result
        validate_lua(result)

    def test_quotes_in_value(self) -> None:
        result = keyword_to_lua_code('general:col he said "hi"')
        assert result is not None
        assert '\\"hi\\"' in result
        validate_lua(result)

    def test_exec_with_special_chars(self) -> None:
        result = dispatch_to_lua_call('exec sh -c "echo hello && exit"')
        assert result is not None
        validate_lua(result)
