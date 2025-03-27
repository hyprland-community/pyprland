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

In case you want to save some time when interacting with the daemon, the simplest is to use one of the `pypr-client` implementations as mentioned in the [getting started page](./Getting-started.md). If for some reason `pypr-client` isn't made available by the package of your OS and can not compile code,
you can use `socat` instead (needs to be installed).

Example of a `pypr-cli` command (should be reachable from your environment's `PATH`):
```sh
#!/bin/sh
socat - "UNIX-CONNECT:${XDG_RUNTIME_DIR}/hypr/${HYPRLAND_INSTANCE_SIGNATURE}/.pyprland.sock" <<< $@
```
On slow systems this may make a difference.
Note that the "help" command will require usage of the standard `pypr` command.
