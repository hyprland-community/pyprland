"""Hyprland compositor backend implementation.

Primary backend for Hyprland, using its Unix socket IPC protocol.
Provides full functionality including batched commands, JSON queries,
and Hyprland-specific event parsing.
"""

from logging import Logger
from typing import Any, cast

from ..ipc import get_response, hyprctl_connection, retry_on_reset
from ..models import ClientInfo, MonitorInfo
from .backend import EnvironmentBackend
from .notifier import HyprlandNotifier, Notifier

# Window rule effects that take a boolean value in the Lua API
_BOOL_EFFECTS = frozenset({
    "float", "tile", "fullscreen", "maximize", "center", "pseudo",
    "no_initial_focus", "pin", "no_anim", "no_blur", "dim_around",
    "decorate", "focus_on_activate", "keep_aspect_ratio", "nearest_neighbor",
    "persistent_size", "allows_input",
})

# Config key suffixes that represent booleans
_BOOL_CONFIG_KEYS = frozenset({"enabled"})


def _is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def _lua_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _lua_bool(value: str) -> str:
    return "true" if value.lower() in ("on", "true", "1") else "false"


def _effect_lua(key: str, value: str) -> str:
    """Render a window rule effect as a Lua key=value pair."""
    if key in _BOOL_EFFECTS:
        return f"{key}={_lua_bool(value) if value else 'true'}"
    if value:
        return f"{key}={_lua_string(value)}"
    return f"{key}=true"


def _named_wr_to_lua(cmd: str) -> str | None:
    """Translate windowrule[name]:key [value] to Lua."""
    end = cmd.find("]")
    if end == -1 or len(cmd) <= end + 1 or cmd[end + 1] != ":":
        return None
    name = cmd[len("windowrule["):end]
    rest = cmd[end + 2:]  # skip ]:

    if rest.startswith("enable "):
        val = rest[len("enable "):].strip()
        enabled = val.lower() in ("true", "1", "on")
        return f'hl.window_rule({{name={_lua_string(name)}, enabled={"true" if enabled else "false"}}})'

    if rest.startswith("match:"):
        match_inner = rest[len("match:"):]
        parts = match_inner.split(" ", 1)
        mk = parts[0]
        mv = parts[1].strip() if len(parts) > 1 else ""
        return f'hl.window_rule({{name={_lua_string(name)}, match={{{mk}={_lua_string(mv)}}}}})'

    parts = rest.split(" ", 1)
    ek = parts[0]
    ev = parts[1].strip() if len(parts) > 1 else ""
    return f'hl.window_rule({{name={_lua_string(name)}, {_effect_lua(ek, ev)}}})'


def _anon_wr_to_lua(cmd: str) -> str | None:
    """Translate windowrule effect [...], [match] to Lua."""
    rest = cmd[len("windowrule "):].strip()

    effect_str = rest
    match_lua = ""

    for sep in (", match:", ", class:"):
        idx = rest.find(sep)
        if idx != -1:
            effect_str = rest[:idx].strip()
            match_raw = rest[idx + 2:].strip()  # skip ", "
            if match_raw.startswith("match:"):
                inner = match_raw[len("match:"):]
                parts = inner.split(" ", 1)
                mk, mv = parts[0], (parts[1].strip() if len(parts) > 1 else "")
                match_lua = f"match={{{mk}={_lua_string(mv)}}}"
            elif ":" in match_raw:
                colon = match_raw.find(":")
                mk = match_raw[:colon].strip()
                mv = match_raw[colon + 1:].strip()
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
    rest = cmd[len("workspace "):].strip()

    comma = rest.find(", ")
    if comma == -1:
        return f"hl.workspace_rule({{workspace={_lua_string(rest)}}})"

    ws_name = rest[:comma]
    opts_str = rest[comma + 2:]
    opts = {}
    for opt in opts_str.split(","):
        opt = opt.strip()
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


def _monitor_to_lua(cmd: str) -> str | None:
    """Translate monitor name,action to Lua."""
    rest = cmd[len("monitor "):].strip()
    if "," not in rest:
        return None
    comma = rest.find(",")
    name = rest[:comma].strip()
    action = rest[comma + 1:].strip()
    if action == "disable":
        return f"hl.monitor({{output={_lua_string(name)}, disabled=true}})"
    return None


def _config_to_lua(cmd: str) -> str | None:
    """Translate config:key value to Lua hl.config() call."""
    sp = cmd.find(" ")
    if sp == -1:
        return None
    key = cmd[:sp]
    value = cmd[sp + 1:].strip()
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


def _keyword_to_lua_code(cmd: str) -> str | None:
    """Translate a Hyprland keyword IPC command to a Lua eval expression.

    Returns None when no translation is available.
    """
    cmd = cmd.strip()
    if cmd.startswith("windowrule["):
        return _named_wr_to_lua(cmd)
    if cmd.startswith("windowrule "):
        return _anon_wr_to_lua(cmd)
    if cmd.startswith("workspace "):
        return _workspace_to_lua(cmd)
    if cmd.startswith("monitor "):
        return _monitor_to_lua(cmd)
    sp = cmd.find(" ")
    if sp > 0 and ":" in cmd[:sp]:
        return _config_to_lua(cmd)
    return None


def _dispatch_to_lua_call(cmd: str) -> str | None:
    """Translate a legacy dispatch command to a Lua hl.dsp.*({}) call.

    The returned string is passed as-is to the hyprctl 'dispatch' IPC command,
    which wraps it as hl.dispatch(returned_string) internally for Lua configs.
    Returns None when the command has no known translation.
    """
    cmd = cmd.strip()

    # movetoworkspacesilent ws,window  — silent means follow=false
    if cmd.startswith("movetoworkspacesilent "):
        rest = cmd[len("movetoworkspacesilent "):].strip()
        ws, sep, window = rest.partition(",")
        if sep:
            return f"hl.dsp.window.move({{workspace={_lua_string(ws.strip())}, follow=false, window={_lua_string(window.strip())}}})"
        return f"hl.dsp.window.move({{workspace={_lua_string(rest)}, follow=false}})"

    # movetoworkspace ws,window
    if cmd.startswith("movetoworkspace "):
        rest = cmd[len("movetoworkspace "):].strip()
        ws, sep, window = rest.partition(",")
        if sep:
            return f"hl.dsp.window.move({{workspace={_lua_string(ws.strip())}, window={_lua_string(window.strip())}}})"
        return f"hl.dsp.window.move({{workspace={_lua_string(rest)}}})"

    # movewindowpixel exact X Y,window
    if cmd.startswith("movewindowpixel "):
        rest = cmd[len("movewindowpixel "):].strip()
        if rest.startswith("exact "):
            rest = rest[len("exact "):].strip()
            coords, sep, window = rest.partition(",")
            if sep:
                parts = coords.split()
                if len(parts) == 2:
                    return f"hl.dsp.window.move({{x={parts[0]}, y={parts[1]}, window={_lua_string(window.strip())}}})"

    # resizewindowpixel exact W H,window
    if cmd.startswith("resizewindowpixel "):
        rest = cmd[len("resizewindowpixel "):].strip()
        if rest.startswith("exact "):
            rest = rest[len("exact "):].strip()
            dims, sep, window = rest.partition(",")
            if sep:
                parts = dims.split()
                if len(parts) == 2:
                    return f"hl.dsp.window.resize({{x={parts[0]}, y={parts[1]}, window={_lua_string(window.strip())}}})"

    # tagwindow [+/-]tag address:0x...
    if cmd.startswith("tagwindow "):
        rest = cmd[len("tagwindow "):].strip()
        tag, sep, window = rest.partition(" ")
        if sep and window:
            return f"hl.dsp.window.tag({{tag={_lua_string(tag)}, window={_lua_string(window.strip())}}})"
        return f"hl.dsp.window.tag({{tag={_lua_string(tag)}}})"

    # focuswindow address:0x...
    if cmd.startswith("focuswindow "):
        window = cmd[len("focuswindow "):].strip()
        return f"hl.dsp.focus({{window={_lua_string(window)}}})"

    # pin [address:0x...]
    if cmd.startswith("pin "):
        window = cmd[len("pin "):].strip()
        return f"hl.dsp.window.pin({{window={_lua_string(window)}}})"
    if cmd == "pin":
        return "hl.dsp.window.pin({})"

    # togglefloating [address:0x...]
    if cmd.startswith("togglefloating "):
        window = cmd[len("togglefloating "):].strip()
        return f"hl.dsp.window.float({{window={_lua_string(window)}}})"
    if cmd == "togglefloating":
        return "hl.dsp.window.float({})"

    # closewindow address:0x...
    if cmd.startswith("closewindow "):
        window = cmd[len("closewindow "):].strip()
        return f"hl.dsp.window.close({{window={_lua_string(window)}}})"

    # alterzorder mode,address:0x...
    if cmd.startswith("alterzorder "):
        rest = cmd[len("alterzorder "):].strip()
        mode, sep, window = rest.partition(",")
        if sep:
            return f"hl.dsp.window.alter_zorder({{mode={_lua_string(mode.strip())}, window={_lua_string(window.strip())}}})"

    # moveworkspacetomonitor workspace monitor
    if cmd.startswith("moveworkspacetomonitor "):
        rest = cmd[len("moveworkspacetomonitor "):].strip()
        ws, sep, mon = rest.partition(" ")
        if sep:
            return f"hl.dsp.workspace.move({{id={_lua_string(ws.strip())}, monitor={_lua_string(mon.strip())}}})"

    # swapactiveworkspaces mon1 mon2
    if cmd.startswith("swapactiveworkspaces "):
        rest = cmd[len("swapactiveworkspaces "):].strip()
        mon1, sep, mon2 = rest.partition(" ")
        if sep:
            return f"hl.dsp.workspace.swap_monitors({{monitor1={_lua_string(mon1.strip())}, monitor2={_lua_string(mon2.strip())}}})"

    # togglespecialworkspace [name]  — Lua prepends "special:" internally
    if cmd.startswith("togglespecialworkspace "):
        name = cmd[len("togglespecialworkspace "):].strip()
        return f"hl.dsp.workspace.toggle_special({_lua_string(name)})"
    if cmd == "togglespecialworkspace":
        return 'hl.dsp.workspace.toggle_special("")'

    # dpms on/off [monitor]
    if cmd.startswith("dpms "):
        rest = cmd[len("dpms "):].strip()
        action, sep, mon = rest.partition(" ")
        if sep:
            return f"hl.dsp.dpms({{action={_lua_string(action.strip())}, monitor={_lua_string(mon.strip())}}})"
        return f"hl.dsp.dpms({{action={_lua_string(action)}}})"

    # execr cmd
    if cmd.startswith("execr "):
        return f"hl.dsp.exec_raw({_lua_string(cmd[len('execr '):].strip())})"

    # exec cmd
    if cmd.startswith("exec "):
        return f"hl.dsp.exec_cmd({_lua_string(cmd[len('exec '):].strip())})"

    return None


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

    def _translate_commands(self, command: str | list, base_command: str, log: Logger) -> tuple[str | list, str]:
        """Translate legacy IPC commands to Lua equivalents for the Lua config parser.

        keyword → eval with hl.config/hl.window_rule/etc.
        dispatch → dispatch with hl.dsp.*({}) (Hyprland wraps these in hl.dispatch() internally)
        """
        if base_command == "keyword":
            translator = _keyword_to_lua_code
            new_base = "eval"
            warn_label = "keyword"
        else:
            translator = _dispatch_to_lua_call
            new_base = "dispatch"
            warn_label = "dispatch"

        if isinstance(command, list):
            translated = []
            for cmd in command:
                if isinstance(cmd, str):
                    result = translator(cmd)
                    if result:
                        translated.append(result)
                    else:
                        log.warning("No Lua translation for %s: %s", warn_label, cmd)
                        translated.append(cmd)
                else:
                    translated.append(cmd)
            return translated, new_base

        result = translator(str(command))
        if result:
            return result, new_base
        log.warning("No Lua translation for %s: %s", warn_label, command)
        return command, base_command

    @retry_on_reset
    async def execute(self, command: str | list | dict, *, log: Logger, **kwargs: Any) -> bool:
        """Execute a command (or list of commands).

        Args:
            command: The command to execute
            log: Logger to use for this operation
            **kwargs: Additional arguments (base_command, weak, etc.)
        """
        base_command = kwargs.get("base_command", "dispatch")
        weak = kwargs.get("weak", False)

        # Lua config dropped support for `keyword` and changed `dispatch` syntax — translate both.
        if self.state.hyprland_config_lua and base_command in ("keyword", "dispatch"):
            command, base_command = self._translate_commands(command, base_command, log)

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
    async def execute_json(self, command: str, *, log: Logger, **kwargs: Any) -> Any:
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
            and (workspace is None or client["workspace"]["name"] == workspace)
            and (workspace_bl is None or client["workspace"]["name"] != workspace_bl)
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

    def parse_event(self, raw_data: str, *, log: Logger) -> tuple[str, Any] | None:
        """Parse a raw event string into (event_name, event_data).

        Args:
            raw_data: Raw event string from the compositor
            log: Logger to use for this operation (unused in Hyprland - simple parsing)
        """
        if ">>" not in raw_data:
            return None
        cmd, params = raw_data.split(">>", 1)
        return f"event_{cmd}", params.rstrip("\n")

    def get_default_notifier(self) -> Notifier:
        """Return Hyprland's native notifier using hyprctl notify."""
        return HyprlandNotifier(self.execute)
