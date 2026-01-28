# Commands

<script setup>
import BuiltinCommands from './components/BuiltinCommands.vue'
</script>

This page covers the `pypr` command-line interface and available commands.

## Overview

The `pypr` command operates in two modes:

| Usage | Mode | Description |
|-------|------|-------------|
| `pypr` | Daemon | Starts the Pyprland daemon (foreground) |
| `pypr <command>` | Client | Sends a command to the running daemon |


There is also an optional `pypr-client` command which is designed for running in keyboard-bindings since it starts faster but doesn't support every built-in command (eg: `validate`, `edit`).

> [!tip]
> Command names can use dashes or underscores interchangeably.
> E.g., `pypr shift_monitors` and `pypr shift-monitors` are equivalent.

## Built-in Commands

These commands are always available, regardless of which plugins are loaded:

<BuiltinCommands />

## Plugin Commands

Each plugin can add its own commands. Use `pypr help` to see the commands made available by the list of plugins you set in your configuration file.

Examples:
- `scratchpads` plugin adds: `toggle`, `show`, `hide`
- `magnify` plugin adds: `zoom`
- `expose` plugin adds: `expose`

See individual [plugin documentation](./Plugins) for command details.

## Shell Completions {#command-compgen}

Pyprland can generate shell completions dynamically based on your loaded plugins and configuration.

### Generating Completions

With the daemon running:

```sh
# Output to stdout (redirect to file)
pypr compgen zsh > ~/.zsh/completions/_pypr

# Install to default user path
pypr compgen bash default
pypr compgen zsh default
pypr compgen fish default

# Install to custom path (absolute or ~/)
pypr compgen bash ~/custom/path/pypr
pypr compgen zsh /etc/zsh/completions/_pypr
```

> [!warning]
> Relative paths may not do what you expect. Use `default`, an absolute path, or a `~/` path.

### Default Installation Paths

| Shell | Default Path |
|-------|--------------|
| Bash | `~/.local/share/bash-completion/completions/pypr` |
| Zsh | `~/.zsh/completions/_pypr` |
| Fish | `~/.config/fish/completions/pypr.fish` |

> [!tip]
> For Zsh, the default path may not be in your `$fpath`. Pypr will show instructions to add it.

> [!note]
> Regenerate completions after adding new plugins or scratchpads to keep them up to date.

## pypr-client {#pypr-client}

`pypr-client` is a lightweight, compiled alternative to `pypr` for sending commands to the daemon. It's significantly faster and ideal for key bindings.

### When to Use It

- In `hyprland.conf` key bindings where startup time matters
- When you need minimal latency (e.g., toggling scratchpads)

### Limitations

- Cannot run the daemon (use `pypr` for that)
- Does not support `validate` or `edit` commands (these require Python)

### Installation

Depending on your installation method, `pypr-client` may already be available. If not:

1. Download the [source code](https://github.com/hyprland-community/pyprland/tree/main/client/)
2. Compile it: `gcc -o pypr-client pypr-client.c`

Rust and Go versions are also available in the same directory.

### Usage in hyprland.conf

```ini
# Use pypr-client for faster key bindings
$pypr = /usr/bin/pypr-client

bind = $mainMod, A, exec, $pypr toggle term
bind = $mainMod, B, exec, $pypr expose
bind = $mainMod SHIFT, Z, exec, $pypr zoom
```

> [!tip]
> If using [uwsm](https://github.com/Vladimir-csp/uwsm), wrap the command:
> ```ini
> $pypr = uwsm-app -- /usr/bin/pypr-client
> ```

For technical details about the client-daemon protocol, see [Architecture: Socket Protocol](./Architecture_core#pyprland-socket-protocol).

## Debugging

To run the daemon with debug logging:

```sh
pypr --debug $HOME/pypr.log
```

Or in `hyprland.conf`:

```ini
exec-once = /usr/bin/pypr --debug $HOME/pypr.log
```

The log file will contain detailed information useful for troubleshooting.
