## Optimizing

### Plugins

- Only enable the plugins you are using in the `plugins` array (in `[pyprland]` section).
- Leaving the configuration for plugins which are not enabled will have no impact.
- Using multiple configuration files only have a small impact on the startup time.

### Pypr

You can run `pypr` using `pypy` (version 3) for a more snappy experience.
One way is to use a `pypy3` virtual environment:

```bash
pypy3 -m venv pypr-venv
source ./pypr-venv/bin/activate
cd <pypr source folder>
pip install -e .
```

### Pypr command

In case you want to save some time when interacting with the daemon, the simplest is to use `pypr-client`. See [Commands: pypr-client](./Commands#pypr-client) for details. If `pypr-client` isn't available from your OS package and you cannot compile code,
you can use `socat` instead (needs to be installed).

Example of a `pypr-cli` command (should be reachable from your environment's `PATH`):

#### Hyprland
```sh
#!/bin/sh
socat - "UNIX-CONNECT:${XDG_RUNTIME_DIR}/hypr/${HYPRLAND_INSTANCE_SIGNATURE}/.pyprland.sock" <<< $@
```

#### Niri
```sh
#!/bin/sh
socat - "UNIX-CONNECT:$(dirname ${NIRI_SOCKET})/.pyprland.sock" <<< $@
```

#### Standalone (other window manager)
```sh
#!/bin/sh
socat - "UNIX-CONNECT:${XDG_DATA_HOME:-$HOME/.local/share}/.pyprland.sock" <<< $@
```

On slow systems this may make a difference.
Note that `validate` and `edit` commands require the standard `pypr` command.
