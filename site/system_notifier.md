---
---
# system_notifier

This plugin adds system notifications based on journal logs (or any program's output).
It monitors specified **sources** for log entries matching predefined **patterns** and generates notifications accordingly (after applying an optional **filter**).

Sources are commands that return a stream of text (eg: journal, mqtt, `tail -f`, ...) which is sent to a parser that will use a [regular expression pattern](https://en.wikipedia.org/wiki/Regular_expression) to detect lines of interest and optionally transform them before sending the notification.

<details>
    <summary>Minimal configuration</summary>

```toml
[[system_notifier.sources]]
command = "journalctl -fx"
parser = "journal"
```

No **sources** are defined by default, so you will need to define at least one.

In general you will also need to define some **parsers**.
By default a **"journal"** parser is provided, otherwise you need to define your own rules.
This built-in configuration is close to this one, provided as an example:

```toml
[[system_notifier.parsers.journal]]
pattern = "([a-z0-9]+): Link UP$"
filter = "s/.*\[\d+\]: ([a-z0-9]+): Link.*/\1 is active/"
color = "#00aa00"

[[system_notifier.parsers.journal]]
pattern = "([a-z0-9]+): Link DOWN$"
filter = "s/.*\[\d+\]: ([a-z0-9]+): Link.*/\1 is inactive/"
color = "#ff8800"
duration = 15

[[system_notifier.parsers.journal]]
pattern = "Process \d+ \(.*\) of .* dumped core."
filter = "s/.*Process \d+ \((.*)\) of .* dumped core./\1 dumped core/"
color = "#aa0000"

[[system_notifier.parsers.journal]]
pattern = "usb \d+-[0-9.]+: Product: "
filter = "s/.*usb \d+-[0-9.]+: Product: (.*)/USB plugged: \1/"
```
</details>

## Commands

<PluginCommands plugin="system_notifier" />

## Configuration

<PluginConfig plugin="system_notifier" linkPrefix="config-" />

### `sources` <ConfigBadges plugin="system_notifier" option="sources" /> {#config-sources}

List of sources to monitor. Each source must contain a `command` to run and a `parser` to use:

```toml
[[system_notifier.sources]]
command = "journalctl -fx"
parser = "journal"
```

You can also use multiple parsers:

```toml
[[system_notifier.sources]]
command = "sudo journalctl -fkn"
parser = ["journal", "custom_parser"]
```

### `parsers` <ConfigBadges plugin="system_notifier" option="parsers" /> {#config-parsers}

Named parser configurations. Each parser rule contains:
- `pattern`: regex to match lines of interest
- `filter`: optional [filter](./filters) to transform text (e.g., `s/.*value: (\d+)/Value=\1/`)
- `color`: optional color in `"#hex"` or `"rgb()"` format
- `duration`: notification display time in seconds (default: 3)

```toml
[[system_notifier.parsers.custom_parser]]
pattern = 'special value:'
filter = "s/.*special value: (\d+)/Value=\1/"
color = "#FF5500"
duration = 10
```

### Built-in "journal" parser

A `journal` parser is provided, detecting link up/down, core dumps, and USB plugs.

### `use_notify_send` <ConfigBadges plugin="system_notifier" option="use_notify_send" /> {#config-use-notify-send}

When enabled, forces use of `notify-send` command instead of the compositor's native notification system.
