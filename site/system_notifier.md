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


## Configuration

### `sources` (recommended)

List of sources to enable (by default nothing is enabled)

Each source must contain a `command` to run and a `parser` to use.

You can also use a list of parsers, eg:

```toml
[[system_notifier.sources]]
command = "sudo journalctl -fkn"
parser = ["journal", "custom_parser"]
```

#### command (recommended)

This is the long-running command (eg: `tail -f <filename>`) returning the stream of text that will be updated. Aa common option is the system journal output (eg: `journalctl -u nginx`)

#### parser

Sets the list of rules / parser to be used to extract lines of interest.
Must match a list of rules defined as `system_notifier.parsers.<parser_name>`.

### `parsers` (recommended)

A list of available parsers that can be used to detect lines of interest in the **sources** and re-format it before issuing a notification.

Each parser definition must contain a **pattern** and optionally a **filter**, **color** and **duration**.

#### pattern

```toml
[[system_notifier.parsers.custom_parser]]
pattern = 'special value:'
```

The pattern is any regular expression.

#### filter

The [filters](./filters) allows to change the text before the notification, eg:
`filter="s/.*special value: (\d+)/Value=\1/"`
will set a filter so a string "special value: 42" will lead to the notification "Value=42"

#### color

You can also provide an optional **color** in `"hex"` or `"rgb()"` format

```toml
color = "#FF5500"
```

#### duration

Notifications display for 3 seconds by default. To change how long they display, use `duration`, which is expressed in seconds.

```toml
[[system_notifier.parsers.custom_parser]]
pattern = 'special value:'
duration = 10
```

### use_notify_send

If you want your notifications to display in your desktop environment's preferred notification UI rather than Hyprland's native notifications, you can set `use_notify_send` to `true`. This will send them via [libnotify](https://gitlab.gnome.org/GNOME/libnotify) using the [`notify-send`](https://man.archlinux.org/man/notify-send.1) command.

```toml
[system_notifier]
use_notify_send = true
```

### default_color

Sets the notification color that will be used when none is provided in a *parser* definition.

```toml
[system_notifier]
default_color = "#bbccbb"
```
