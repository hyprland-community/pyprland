"""Lua translation layer for Hyprland IPC commands.

Translates legacy hyprlang keyword/dispatch commands to their Lua equivalents
for Hyprland >= 0.55 which uses Lua as its config language.

Keyword commands become `hl.config()`/`hl.window_rule()`/etc. via eval.
Dispatch commands become `hl.dsp.*({})` calls.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

# Window rule effects that take a boolean value in the Lua API
_BOOL_EFFECTS = frozenset(
    {
        "float",
        "tile",
        "fullscreen",
        "maximize",
        "center",
        "pseudo",
        "no_initial_focus",
        "pin",
        "no_anim",
        "no_blur",
        "dim_around",
        "decorate",
        "focus_on_activate",
        "keep_aspect_ratio",
        "nearest_neighbor",
        "persistent_size",
        "allows_input",
    }
)

# Config key suffixes that represent booleans
_BOOL_CONFIG_KEYS = frozenset({"enabled"})


# --- Utility helpers ---


def _is_number(s: str) -> bool:
    try:
        float(s)
    except ValueError:
        return False
    else:
        return True


def _lua_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _lua_bool(value: str) -> str:
    return "true" if value.lower() in ("on", "true", "1") else "false"


def _effect_lua(key: str, value: str) -> str:
    """Render a window rule effect as a Lua key=value pair."""
    if key in _BOOL_EFFECTS:
        return f"{key}={_lua_bool(value) if value else 'true'}"
    if value:
        if _is_number(value):
            return f"{key}={value}"
        return f"{key}={_lua_string(value)}"
    return f"{key}=true"


# --- Keyword translators ---


def _named_wr_to_lua(cmd: str) -> str | None:
    """Translate windowrule[name]:key [value] to Lua."""
    end = cmd.find("]")
    if end == -1 or len(cmd) <= end + 1 or cmd[end + 1] != ":":
        return None
    name = cmd[len("windowrule[") : end]
    rest = cmd[end + 2 :]  # skip ]:

    if rest.startswith("enable "):
        val = rest[len("enable ") :].strip()
        enabled = val.lower() in ("true", "1", "on")
        return f"hl.window_rule({{name={_lua_string(name)}, enabled={'true' if enabled else 'false'}}})"

    if rest.startswith("match:"):
        match_inner = rest[len("match:") :]
        parts = match_inner.split(" ", 1)
        mk = parts[0]
        mv = parts[1].strip() if len(parts) > 1 else ""
        return f"hl.window_rule({{name={_lua_string(name)}, match={{{mk}={_lua_string(mv)}}}}})"

    parts = rest.split(" ", 1)
    ek = parts[0]
    ev = parts[1].strip() if len(parts) > 1 else ""
    return f"hl.window_rule({{name={_lua_string(name)}, {_effect_lua(ek, ev)}}})"


def _anon_wr_to_lua(cmd: str) -> str | None:
    """Translate windowrule effect [...], [match] to Lua."""
    rest = cmd[len("windowrule ") :].strip()

    effect_str = rest
    match_lua = ""

    for sep in (", match:", ", class:"):
        idx = rest.find(sep)
        if idx != -1:
            effect_str = rest[:idx].strip()
            match_raw = rest[idx + 2 :].strip()  # skip ", "
            if match_raw.startswith("match:"):
                inner = match_raw[len("match:") :]
                parts = inner.split(" ", 1)
                mk, mv = parts[0], (parts[1].strip() if len(parts) > 1 else "")
                match_lua = f"match={{{mk}={_lua_string(mv)}}}"
            elif ":" in match_raw:
                colon = match_raw.find(":")
                mk = match_raw[:colon].strip()
                mv = match_raw[colon + 1 :].strip()
                match_lua = f"match={{{mk}={_lua_string(mv)}}}"
            break

    parts = effect_str.split(" ", 1)
    ek = parts[0]
    ev = parts[1].strip() if len(parts) > 1 else ""
    effect_part = _effect_lua(ek, ev)

    inner = effect_part + (", " + match_lua if match_lua else "")
    return f"hl.window_rule({{{inner}}})"


def _workspace_to_lua(cmd: str) -> str | None:
    """Translate workspace name[, options] to Lua."""
    rest = cmd[len("workspace ") :].strip()

    comma = rest.find(", ")
    if comma == -1:
        return f"hl.workspace_rule({{workspace={_lua_string(rest)}}})"

    ws_name = rest[:comma]
    opts_str = rest[comma + 2 :]
    opts = {}
    for raw_opt in opts_str.split(","):
        opt = raw_opt.strip()
        if ":" in opt:
            k, _, v = opt.partition(":")
            k, v = k.strip(), v.strip()
            if v.lower() in ("true", "1", "on"):
                opts[k] = "true"
            elif v.lower() in ("false", "0", "off"):
                opts[k] = "false"
            else:
                opts[k] = _lua_string(v)

    opts_lua = ", ".join(f"{k}={v}" for k, v in opts.items())
    return f"hl.workspace_rule({{workspace={_lua_string(ws_name)}, {opts_lua}}})"


def _animation_to_lua(cmd: str) -> str | None:
    """Translate animations:enabled value to Lua hl.animation() call."""
    rest = cmd[len("animations:enabled") :].strip()
    if not rest:
        return None
    enabled = _lua_bool(rest)
    return f'hl.animation({{leaf="global",enabled={enabled},speed=0,bezier="default"}})'


def _monitor_to_lua(cmd: str) -> str | None:
    """Translate monitor name,action to Lua."""
    rest = cmd[len("monitor ") :].strip()
    if "," not in rest:
        return None
    parts = rest.split(",")
    name = parts[0].strip()
    if len(parts) == 2 and parts[1].strip() == "disable":  # noqa: PLR2004
        return f"hl.monitor({{output={_lua_string(name)}, disabled=true}})"
    if len(parts) >= 4:  # noqa: PLR2004
        # Format: name,RES@RATE,POSxPOS,SCALE[,transform,VALUE]
        mode = parts[1].strip()
        position = parts[2].strip()
        scale = parts[3].strip()
        fields = f"output={_lua_string(name)}, mode={_lua_string(mode)}, position={_lua_string(position)}, scale={scale}"
        if len(parts) >= 6 and parts[4].strip() == "transform":  # noqa: PLR2004
            fields += f", transform={parts[5].strip()}"
        return f"hl.monitor({{{fields}}})"
    return None


def _config_to_lua(cmd: str) -> str | None:
    """Translate config:key value to Lua hl.config() call."""
    sp = cmd.find(" ")
    if sp == -1:
        return None
    key = cmd[:sp]
    value = cmd[sp + 1 :].strip()
    keys = key.split(":")
    last_key = keys[-1]

    if last_key in _BOOL_CONFIG_KEYS:
        lua_val = _lua_bool(value)
    elif _is_number(value):
        lua_val = value
    else:
        lua_val = _lua_string(value)

    inner = f"{last_key}={lua_val}"
    for k in reversed(keys[:-1]):
        inner = f"{k}={{{inner}}}"
    return f"hl.config({{{inner}}})"


# Ordered list of keyword prefix handlers (order matters for overlapping prefixes)
_KEYWORD_HANDLERS: list[tuple[str, Callable[[str], str | None]]] = [
    ("animations:", _animation_to_lua),
    ("windowrule[", _named_wr_to_lua),
    ("windowrule ", _anon_wr_to_lua),
    ("workspace ", _workspace_to_lua),
    ("monitor ", _monitor_to_lua),
]


def keyword_to_lua_code(cmd: str) -> str | None:
    """Translate a Hyprland keyword IPC command to a Lua eval expression.

    Returns None when no translation is available.
    """
    cmd = cmd.strip()
    for prefix, handler in _KEYWORD_HANDLERS:
        if cmd.startswith(prefix):
            return handler(cmd)
    # Fallback: config key (contains ":" before the first space)
    sp = cmd.find(" ")
    if sp > 0 and ":" in cmd[:sp]:
        return _config_to_lua(cmd)
    return None


# --- Dispatch translators ---


def _dsp_movetoworkspacesilent(rest: str) -> str:
    ws, sep, window = rest.partition(",")
    if sep:
        return f"hl.dsp.window.move({{workspace={_lua_string(ws.strip())}, follow=false, window={_lua_string(window.strip())}}})"
    return f"hl.dsp.window.move({{workspace={_lua_string(rest)}, follow=false}})"


def _dsp_movetoworkspace(rest: str) -> str:
    ws, sep, window = rest.partition(",")
    if sep:
        return f"hl.dsp.window.move({{workspace={_lua_string(ws.strip())}, window={_lua_string(window.strip())}}})"
    return f"hl.dsp.window.move({{workspace={_lua_string(rest)}}})"


def _dsp_movewindowpixel(rest: str) -> str | None:
    if rest.startswith("exact "):
        rest = rest[len("exact ") :].strip()
        coords, sep, window = rest.partition(",")
        if sep:
            parts = coords.split()
            if len(parts) == 2:  # noqa: PLR2004
                return f"hl.dsp.window.move({{x={parts[0]}, y={parts[1]}, window={_lua_string(window.strip())}}})"
    return None


def _dsp_resizewindowpixel(rest: str) -> str | None:
    if rest.startswith("exact "):
        rest = rest[len("exact ") :].strip()
        dims, sep, window = rest.partition(",")
        if sep:
            parts = dims.split()
            if len(parts) == 2:  # noqa: PLR2004
                return f"hl.dsp.window.resize({{x={parts[0]}, y={parts[1]}, window={_lua_string(window.strip())}}})"
    return None


def _dsp_tagwindow(rest: str) -> str:
    tag, sep, window = rest.partition(" ")
    if sep and window:
        return f"hl.dsp.window.tag({{tag={_lua_string(tag)}, window={_lua_string(window.strip())}}})"
    return f"hl.dsp.window.tag({{tag={_lua_string(tag)}}})"


def _dsp_focuswindow(rest: str) -> str:
    return f"hl.dsp.focus({{window={_lua_string(rest)}}})"


def _dsp_pin(rest: str) -> str:
    if rest:
        return f"hl.dsp.window.pin({{window={_lua_string(rest)}}})"
    return "hl.dsp.window.pin({})"


def _dsp_togglefloating(rest: str) -> str:
    if rest:
        return f"hl.dsp.window.float({{window={_lua_string(rest)}}})"
    return "hl.dsp.window.float({})"


def _dsp_closewindow(rest: str) -> str:
    return f"hl.dsp.window.close({{window={_lua_string(rest)}}})"


def _dsp_alterzorder(rest: str) -> str | None:
    mode, sep, window = rest.partition(",")
    if sep:
        return f"hl.dsp.window.alter_zorder({{mode={_lua_string(mode.strip())}, window={_lua_string(window.strip())}}})"
    return None


def _dsp_moveworkspacetomonitor(rest: str) -> str | None:
    ws, sep, mon = rest.partition(" ")
    if sep:
        return f"hl.dsp.workspace.move({{id={_lua_string(ws.strip())}, monitor={_lua_string(mon.strip())}}})"
    return None


def _dsp_swapactiveworkspaces(rest: str) -> str | None:
    mon1, sep, mon2 = rest.partition(" ")
    if sep:
        return f"hl.dsp.workspace.swap_monitors({{monitor1={_lua_string(mon1.strip())}, monitor2={_lua_string(mon2.strip())}}})"
    return None


def _dsp_togglespecialworkspace(rest: str) -> str:
    if rest:
        return f"hl.dsp.workspace.toggle_special({_lua_string(rest)})"
    return 'hl.dsp.workspace.toggle_special("")'


def _dsp_dpms(rest: str) -> str:
    action, sep, mon = rest.partition(" ")
    if sep:
        return f"hl.dsp.dpms({{action={_lua_string(action.strip())}, monitor={_lua_string(mon.strip())}}})"
    return f"hl.dsp.dpms({{action={_lua_string(action)}}})"


def _dsp_execr(rest: str) -> str:
    return f"hl.dsp.exec_raw({_lua_string(rest)})"


def _dsp_exec(rest: str) -> str:
    return f"hl.dsp.exec_cmd({_lua_string(rest)})"


def _dsp_movefocus(rest: str) -> str:
    return f"hl.dsp.focus({{direction={_lua_string(rest)}}})"


def _dsp_workspace(rest: str) -> str:
    return f"hl.dsp.focus({{workspace={_lua_string(rest)}}})"


def _dsp_layoutmsg(rest: str) -> str:
    return f"hl.dsp.layout({_lua_string(rest)})"


# Dispatch table mapping command names to their Lua translators.
# Each handler receives the argument portion (after the command name).
_DISPATCH_HANDLERS: dict[str, Callable[[str], str | None]] = {
    "movetoworkspacesilent": _dsp_movetoworkspacesilent,
    "movetoworkspace": _dsp_movetoworkspace,
    "movewindowpixel": _dsp_movewindowpixel,
    "resizewindowpixel": _dsp_resizewindowpixel,
    "tagwindow": _dsp_tagwindow,
    "focuswindow": _dsp_focuswindow,
    "pin": _dsp_pin,
    "togglefloating": _dsp_togglefloating,
    "closewindow": _dsp_closewindow,
    "alterzorder": _dsp_alterzorder,
    "moveworkspacetomonitor": _dsp_moveworkspacetomonitor,
    "swapactiveworkspaces": _dsp_swapactiveworkspaces,
    "togglespecialworkspace": _dsp_togglespecialworkspace,
    "dpms": _dsp_dpms,
    "execr": _dsp_execr,
    "exec": _dsp_exec,
    "movefocus": _dsp_movefocus,
    "workspace": _dsp_workspace,
    "layoutmsg": _dsp_layoutmsg,
}


def dispatch_to_lua_call(cmd: str) -> str | None:
    """Translate a legacy dispatch command to a Lua hl.dsp.*({}) call.

    The returned string is passed as-is to the hyprctl 'dispatch' IPC command,
    which wraps it as hl.dispatch(returned_string) internally for Lua configs.
    Returns None when the command has no known translation.
    """
    cmd = cmd.strip()

    # Passthrough: if the command is already a Lua expression, return as-is
    if cmd.startswith("hl.dsp."):
        return cmd

    name, _, rest = cmd.partition(" ")
    rest = rest.strip()

    handler = _DISPATCH_HANDLERS.get(name)
    if handler:
        return handler(rest)
    return None
