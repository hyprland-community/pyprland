# Development

It's easy to write your own plugin by making a python package and then indicating it's name as the plugin name.

[Contributing guidelines](https://github.com/hyprland-community/pyprland/blob/main/CONTRIBUTING.md)

# Writing plugins

Plugins can be loaded with full python module path, eg: `"mymodule.pyprlandplugin"`, the loaded module must provide an `Extension` class.

Check the `interface.py` file to know the base methods, also have a look at the example below.

To get more details when an error is occurring, use `pypr --debug <log file path>`, it will also display the log in the console.

> [!note]
> To quickly get started, you can directly edit the `experimental` built-in plugin.
> In order to distribute it, make your own Python package or trigger a pull request.
> If you prefer to make a separate package, check the [examples](https://github.com/hyprland-community/pyprland/blob/main/sample_extension/)'s package

The `Extension` interface provides a couple of built-in attributes:

- `config` : object exposing the plugin section in `pyprland.toml`
- `notify` ,`notify_error`, `notify_info` : access to Hyprland's notification system
- `hyprctl`, `hyprctl_json` : invoke [Hyprland's IPC system](https://wiki.hyprland.org/Configuring/Dispatchers/)


> [!important]
> Contact me to get your extension listed on the home page

> [!tip]
> You can set a `plugins_paths=["/custom/path/example"]` in the `hyprland` section of the configuration to add extra paths (eg: during development).

> [!Note]
> If your extension is at the root of the plugin (this is not recommended, preferable add a name space, as in `johns_pyprland.super_feature`, rather than `super_feature`) you can still import it using the `external:` prefix when you refer to it in the `plugins` list.

# API Documentation

Run `tox run -e doc` then visit `http://localhost:8080`

The most important to know are:

- `hyprctl_json` to get a response from an IPC query
- `hyprctl` to trigger general IPC commands
- `on_reload` to be implemented, called when the config is (re)loaded
- `run_<command_name>` to implement a command
- `event_<event_name>` called when the given event is emitted by Hyprland

All those methods are _async_

On top of that:

- the first line of a `run_*` command's docstring will be used by the `help` command
- `self.config` in your _Extension_ contains the entry corresponding to your plugin name in the TOML file
- `state` from `..common` module contains ready to use information
- there is a `MenuMixin` in `..adapters.menus` to make menu-based plugins easy

# Workflow

Just `^C` when you make a change and repeat:

```sh
pypr exit ; pypr --debug /tmp/output.log
```


## Creating a plugin

```python
from .interface import Plugin


class Extension(Plugin):
    " My plugin "

    async def init(self):
        await self.notify("My plugin loaded")
```

## Adding a command

Just add a method called `run_<name of your command>` to your `Extension` class, eg with "togglezoom" command:

```python
    zoomed = False

    async def run_togglezoom(self, args):
        """ this doc string will show in `help` to document `togglezoom`
        But this line will not show in the CLI help
        """
      if self.zoomed:
        await self.hyprctl('misc:cursor_zoom_factor 1', 'keyword')
      else:
        await self.hyprctl('misc:cursor_zoom_factor 2', 'keyword')
      self.zoomed = not self.zoomed
```

## Reacting to an event

Similar as a command, implement some `async def event_<the event you are interested in>` method.

## Code safety

Pypr ensures only one `run_` or `event_` handler runs at a time, allowing the plugins code to stay simple and avoid the need for concurrency handling.
However, each plugin can run its handlers in parallel.

# Reusable code

```py
from ..common import state, CastBoolMixin
```

- `state` provides a couple of handy variables so you don't have to fetch them, allow optimizing the most common operations
- `Mixins` are providing common code, for instance the `CastBoolMixin` provides the `cast_bool` method to your `Extension`.

If you want to use menus, then the `MenuMixin` will provide:
- `menu` to show a menu
- `ensure_menu_configured` to call before you require a menu in your plugin

# Example

You'll find a basic external plugin in the [examples](https://github.com/hyprland-community/pyprland/blob/main/sample_extension/) folder.

It provides one command: `pypr dummy`.

Read the [plugin code](https://github.com/hyprland-community/pyprland/blob/main/sample_extension/pypr_examples/focus_counter.py)

It's a simple python package. To install it for development without a need to re-install it for testing, you can use `pip install -e .` in this folder.
It's ready to be published using `poetry publish`, don't forget to update the details in the `pyproject.toml` file.

## Usage

Ensure you added `pypr_examples.focus_counter` to your `plugins` list:

```toml
[pyprland]
plugins = [
  "pypr_examples.focus_counter"
]
```

Optionally you can customize one color:

```toml
["pypr_examples.focus_counter"]
color = "FFFF00"
```
