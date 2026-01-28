# Troubleshooting

## Checking Logs

How you access logs depends on how you run pyprland.

### Systemd Service

If you run pyprland as a [systemd user service](./Getting-started#option-2-systemd-user-service):

```sh
journalctl --user -u pyprland -f
```

### exec-once (Hyprland)

If you run pyprland via [exec-once](./Getting-started#option-1-hyprland-exec-once), logs go to stderr by default and are typically lost.

To enable debug logging, add `--debug <logfile>` to your exec-once command:

```ini
exec-once = /usr/bin/pypr --debug $HOME/pypr.log
```

Then check the log file:

```sh
tail -f ~/pypr.log
```

> [!tip]
> Use a path like `$HOME/pypr.log` or `/tmp/pypr.log` to avoid cluttering your home directory.

### Running from Terminal

For quick debugging, run pypr directly in a terminal:

```sh
pypr --debug /dev/null
```

This shows debug output directly in the terminal. Use `/dev/null` as the log path to avoid creating a file while still seeing the output.

## General Issues

In case of trouble running a `pypr` command:

1. Kill the existing pypr daemon if running (try `pypr exit` first)
2. Run from a terminal with `--debug` to see error messages

If the client says it can't connect, the daemon likely didn't start. Check if it's running:

```sh
ps aux | grep pypr
```

You can try starting it manually from a terminal:

```sh
pypr --debug /dev/null
```

This will show any startup errors directly in the terminal.

## Force Hyprland Version

In case your `hyprctl version -j` command isn't returning an accurate version, you can make Pyprland ignore it and use a provided value instead:

```toml
[pyprland]
hyprland_version = "0.41.0"
```

## Unresponsive Scratchpads

Scratchpads aren't responding for a few seconds after trying to show one (which didn't show!)

This may happen if an application is very slow to start.
In that case pypr will wait for a window, blocking other scratchpad operations, before giving up after a few seconds.

Note that other plugins shouldn't be blocked by this.

More scratchpads troubleshooting can be found [here](./scratchpads_nonstandard).

## See Also

- [Getting Started: Running the Daemon](./Getting-started#running-the-daemon) - Setup options
- [Commands: Debugging](./Commands#debugging) - Debug flag reference
