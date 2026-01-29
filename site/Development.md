# Development

It's easy to write your own plugin by making a Python package and then indicating its name as the plugin name.

> [!tip]
> For details on internal architecture, data flows, and design patterns, see the [Architecture](./Architecture) document.

[Contributing guidelines](https://github.com/fdev31/pyprland/blob/main/CONTRIBUTING.md)

## Development Setup

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/) for dependency management
- [pre-commit](https://pre-commit.com/) for Git hooks

### Initial Setup

```sh
# Clone the repository
git clone https://github.com/fdev31/pyprland.git
cd pyprland

# Install dependencies
poetry install

# Install dev and lint dependencies
poetry install --with dev,lint

# Install pre-commit hooks
pip install pre-commit
pre-commit install
pre-commit install --hook-type pre-push
```

## Quick Start

### Debugging

To get detailed logs when an error occurs, use:

```sh
pypr --debug
```

This displays logs in the console. To also save logs to a file:

```sh
pypr --debug $HOME/pypr.log
```

### Quick Experimentation

> [!note]
> To quickly get started, you can directly edit the built-in [`experimental`](https://github.com/fdev31/pyprland/blob/main/pyprland/plugins/experimental.py) plugin.
> To distribute your plugin, create your own Python package or submit a pull request.

### Custom Plugin Paths

> [!tip]
> Set `plugins_paths = ["/custom/path"]` in the `[pyprland]` section of your config to add extra plugin search paths during development.

## Writing Plugins

### Plugin Loading

Plugins are loaded by their full Python module path:

```toml
[pyprland]
plugins = ["mypackage.myplugin"]
```

The module must provide an `Extension` class inheriting from [`Plugin`](https://github.com/fdev31/pyprland/blob/main/pyprland/plugins/interface.py).

> [!note]
> If your extension is at the root level (not recommended), you can import it using the `external:` prefix:
> ```toml
> plugins = ["external:myplugin"]
> ```
> Prefer namespaced packages like `johns_pyprland.super_feature` instead.

### Plugin Attributes

Your `Extension` class has access to these attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `self.name` | `str` | Plugin identifier |
| `self.config` | [`Configuration`](https://github.com/fdev31/pyprland/blob/main/pyprland/config.py) | Plugin's TOML config section |
| `self.state` | [`SharedState`](https://github.com/fdev31/pyprland/blob/main/pyprland/common.py) | Shared application state (active workspace, monitor, etc.) |
| `self.backend` | [`EnvironmentBackend`](https://github.com/fdev31/pyprland/blob/main/pyprland/adapters/backend.py) | WM interaction: commands, queries, notifications |
| `self.log` | `Logger` | Plugin-specific logger |

### Creating Your First Plugin

```python
from pyprland.plugins.interface import Plugin


class Extension(Plugin):
    """My custom plugin."""

    async def init(self) -> None:
        """Called once at startup."""
        self.log.info("My plugin initialized")

    async def on_reload(self) -> None:
        """Called on init and config reload."""
        self.log.info(f"Config: {self.config}")

    async def exit(self) -> None:
        """Cleanup on shutdown."""
        pass
```

### Adding Commands

Add `run_<commandname>` methods to handle `pypr <commandname>` calls.

The **first line** of the docstring appears in `pypr help`:

```python
class Extension(Plugin):
    zoomed = False

    async def run_togglezoom(self, args: str) -> str | None:
        """Toggle zoom level.

        This second line won't appear in CLI help.
        """
        if self.zoomed:
            await self.backend.execute("keyword misc:cursor_zoom_factor 1")
        else:
            await self.backend.execute("keyword misc:cursor_zoom_factor 2")
        self.zoomed = not self.zoomed
```

### Reacting to Events

Add `event_<eventname>` methods to react to [Hyprland events](https://wiki.hyprland.org/IPC/):

```python
async def event_openwindow(self, params: str) -> None:
    """React to window open events."""
    addr, workspace, cls, title = params.split(",", 3)
    self.log.debug(f"Window opened: {title}")

async def event_workspace(self, workspace: str) -> None:
    """React to workspace changes."""
    self.log.info(f"Switched to workspace: {workspace}")
```

> [!note]
> **Code Safety:** Pypr ensures only one handler runs at a time per plugin, so you don't need concurrency handling. Each plugin runs independently in parallel. See [Architecture - Manager](./Architecture#manager) for details.

### Configuration Schema

Define expected config fields for automatic validation using [`ConfigField`](https://github.com/fdev31/pyprland/blob/main/pyprland/validation.py):

```python
from pyprland.plugins.interface import Plugin
from pyprland.validation import ConfigField


class Extension(Plugin):
    config_schema = [
        ConfigField("enabled", bool, required=False, default=True),
        ConfigField("timeout", int, required=False, default=5000),
        ConfigField("command", str, required=True),
    ]

    async def on_reload(self) -> None:
        # Config is validated before on_reload is called
        cmd = self.config["command"]  # Guaranteed to exist
```

### Using Menus

For plugins that need menu interaction (rofi, wofi, tofi, etc.), use [`MenuMixin`](https://github.com/fdev31/pyprland/blob/main/pyprland/adapters/menus.py):

```python
from pyprland.adapters.menus import MenuMixin
from pyprland.plugins.interface import Plugin


class Extension(MenuMixin, Plugin):
    async def run_select(self, args: str) -> None:
        """Show a selection menu."""
        await self.ensure_menu_configured()

        options = ["Option 1", "Option 2", "Option 3"]
        selected = await self.menu(options, "Choose an option:")

        if selected:
            await self.backend.notify_info(f"Selected: {selected}")
```

## Reusable Code

### Shared State

Access commonly needed information without fetching it:

```python
# Current workspace, monitor, window
workspace = self.state.active_workspace
monitor = self.state.active_monitor
window_addr = self.state.active_window

# Environment detection
if self.state.environment == "niri":
    # Niri-specific logic
    pass
```

See [Architecture - Shared State](./Architecture#shared-state) for all available fields.

### Mixins

Use mixins for common functionality:

```python
from pyprland.common import CastBoolMixin
from pyprland.plugins.interface import Plugin


class Extension(CastBoolMixin, Plugin):
    async def on_reload(self) -> None:
        # Safely cast config values to bool
        enabled = self.cast_bool(self.config.get("enabled", True))
```

## Development Workflow

Restart the daemon after making changes:

```sh
pypr exit ; pypr --debug
```

### API Documentation

Generate and browse the full API documentation:

```sh
tox run -e doc
# Then visit http://localhost:8080
```

## Testing & Quality Assurance

### Running All Checks

Before submitting a PR, run the full test suite:

```sh
tox
```

This runs unit tests across Python versions and linting checks.

### Tox Environments

| Environment | Command | Description |
|-------------|---------|-------------|
| `py314-unit` | `tox run -e py314-unit` | Unit tests (Python 3.14) |
| `py311-unit` | `tox run -e py311-unit` | Unit tests (Python 3.11) |
| `py312-unit` | `tox run -e py312-unit` | Unit tests (Python 3.12) |
| `py314-linting` | `tox run -e py314-linting` | Full linting suite (mypy, ruff, pylint, flake8) |
| `py314-wiki` | `tox run -e py314-wiki` | Check plugin documentation coverage |
| `doc` | `tox run -e doc` | Generate API docs with pdoc |
| `coverage` | `tox run -e coverage` | Run tests with coverage report |
| `deadcode` | `tox run -e deadcode` | Detect dead code with vulture |

### Quick Test Commands

```sh
# Run unit tests only
tox run -e py314-unit

# Run linting only
tox run -e py314-linting

# Check documentation coverage
tox run -e py314-wiki

# Run tests with coverage
tox run -e coverage
```

## Pre-commit Hooks

Pre-commit hooks ensure code quality before commits and pushes.

### Installation

```sh
pip install pre-commit
pre-commit install
pre-commit install --hook-type pre-push
```

### What Runs Automatically

**On every commit:**

| Hook | Purpose |
|------|---------|
| `versionMgmt` | Auto-increment version number |
| `wikiDocGen` | Regenerate plugin documentation JSON |
| `wikiDocCheck` | Verify documentation coverage |
| `ruff-check` | Lint Python code |
| `ruff-format` | Format Python code |
| `flake8` | Additional Python linting |
| `check-yaml` | Validate YAML files |
| `check-json` | Validate JSON files |
| `pretty-format-json` | Auto-format JSON files |
| `beautysh` | Format shell scripts |
| `yamllint` | Lint YAML files |

**On push:**

| Hook | Purpose |
|------|---------|
| `runtests` | Run full pytest suite |

### Manual Execution

Run all hooks manually:

```sh
pre-commit run --all-files
```

Run a specific hook:

```sh
pre-commit run ruff-check --all-files
```

## Packaging & Distribution

### Creating an External Plugin Package

See the [sample extension](https://github.com/fdev31/pyprland/tree/main/sample_extension) for a complete example with:
- Proper package structure
- `pyproject.toml` configuration
- Example plugin code: [`focus_counter.py`](https://github.com/fdev31/pyprland/blob/main/sample_extension/pypr_examples/focus_counter.py)

### Development Installation

Install your package in editable mode for testing:

```sh
cd your-plugin-package/
pip install -e .
```

### Publishing

When ready to distribute:

```sh
poetry publish
```

Don't forget to update the details in your `pyproject.toml` file first.

### Example Usage

Add your plugin to the config:

```toml
[pyprland]
plugins = ["pypr_examples.focus_counter"]

["pypr_examples.focus_counter"]
multiplier = 2
```

> [!important]
> Contact the maintainer to get your extension listed on the home page.

## Further Reading

- [Architecture](./Architecture) - Internal system design, data flows, and design patterns
- [Plugins](./Plugins) - List of available built-in plugins
- [Sample Extension](https://github.com/fdev31/pyprland/tree/main/sample_extension) - Complete example plugin package
- [Hyprland IPC](https://wiki.hyprland.org/IPC/) - Hyprland's IPC documentation
