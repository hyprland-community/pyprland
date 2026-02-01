# Getting Started

Pypr consists of two things:

- **A tool**: `pypr` which runs the daemon (service) and allows you to interact with it
- **A config file**: `~/.config/hypr/pyprland.toml` using the [TOML](https://toml.io/en/) format

> [!important]
> - With no arguments, `pypr` runs the daemon (doesn't fork to background)
> - With arguments, it sends commands to the running daemon

> [!tip]
> For keybindings, use `pypr-client` instead of `pypr` for faster response (~1ms vs ~50ms). See [Commands: pypr-client](./Commands#pypr-client) for details.

## Installation

Check your OS package manager first:

- **Arch Linux**: Available on AUR, e.g., with [yay](https://github.com/Jguer/yay): `yay pyprland`
- **NixOS**: See the [Nix](./Nix) page for instructions

Otherwise, install via pip (preferably in a [virtual environment](./InstallVirtualEnvironment)):

```sh
pip install pyprland
```

## Minimal Configuration

Create `~/.config/hypr/pyprland.toml` with:

```toml
[pyprland]
plugins = [
    "scratchpads",
    "magnify",
]
```

This enables two popular plugins. See the [Plugins](./Plugins) page for the full list.

## Running the Daemon

> [!caution]
> If you installed pypr outside your OS package manager (e.g., pip, virtual environment), use the full path to the `pypr` command. Get it with `which pypr` in a working terminal.

### Option 1: Hyprland exec-once

Add to your `hyprland.conf`:

```ini
exec-once = /usr/bin/pypr
```

For debugging, use:

```ini
exec-once = /usr/bin/pypr --debug
```

Or to also save logs to a file:

```ini
exec-once = /usr/bin/pypr --debug $HOME/pypr.log
```

### Option 2: Systemd User Service

Create `~/.config/systemd/user/pyprland.service`:

```ini
[Unit]
Description=Starts pyprland daemon
After=graphical-session.target
Wants=graphical-session.target
# Optional: wait for other services to start first
# Wants=hyprpaper.service
StartLimitIntervalSec=600
StartLimitBurst=5

[Service]
Type=simple
# Optional: only start on specific compositor
# For Hyprland:
# ExecStartPre=/bin/sh -c '[ "$XDG_CURRENT_DESKTOP" = "Hyprland" ] || exit 0'
# For Niri:
# ExecStartPre=/bin/sh -c '[ "$XDG_CURRENT_DESKTOP" = "niri" ] || exit 0'
ExecStart=pypr
Restart=always

[Install]
WantedBy=graphical-session.target
```

Then enable and start the service:

```sh
systemctl enable --user --now pyprland.service
```

## Verifying It Works

Once the daemon is running, check available commands:

```sh
pypr help
```

If something isn't working, check the [Troubleshooting](./Troubleshooting) page.

## Next Steps

- [Configuration](./Configuration) - Full configuration reference
- [Commands](./Commands) - CLI commands and shell completions
- [Plugins](./Plugins) - Browse available plugins
- [Examples](./Examples) - Complete configuration examples
