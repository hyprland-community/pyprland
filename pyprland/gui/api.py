"""API logic for the pyprland GUI: schema serialization, config I/O, validation.

Bridges the existing pyprland infrastructure (discovery, validation, generator)
into JSON-friendly structures consumed by the Vue.js frontend.

Config layout convention managed by the GUI:

* **Main file** (``config.toml``): ``[pyprland]`` section with ``plugins``
  (only plugins that have **no config data**), ``include``, and other core
  keys.  No plugin config sections live here.
* **Per-plugin files** (``conf.d/<plugin>.toml``): Each file carries
  ``[pyprland] plugins = ["<name>"]`` **plus** all config sections for that
  plugin.  Created only when the plugin has actual config data.
* **Variables** (``conf.d/variables.toml``): ``[pyprland.variables]`` section.
* On save the GUI **normalises** ``conf.d/`` to one-plugin-per-file, backing
  up any composite files it rewrites.
"""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from ..config_loader import load_config, load_toml, resolve_config_path
from ..constants import CONTROL
from ..quickstart.discovery import PluginInfo, discover_plugins
from ..quickstart.generator import (
    backup_config,
    format_toml_value,
    generate_toml,
    get_config_path,
)
from ..validation import ConfigField, ConfigItems, ConfigValidator

if TYPE_CHECKING:
    from pathlib import Path

__all__ = [
    "apply_config",
    "get_config",
    "get_plugins_schema",
    "save_config",
    "validate_config",
]

_log = logging.getLogger("pypr-gui.api")


# ---------------------------------------------------------------------------
#  Schema serialization
# ---------------------------------------------------------------------------


def _field_to_dict(field: ConfigField) -> dict[str, Any]:
    """Serialize a ConfigField to a JSON-friendly dict."""
    result: dict[str, Any] = {
        "name": field.name,
        "type": field.type_name,
        "description": field.description,
        "category": field.category or "general",
        "required": field.required,
        "recommended": field.recommended,
    }

    if field.default is not None:
        result["default"] = field.default
    if field.choices is not None:
        result["choices"] = field.choices
    if field.children is not None:
        result["children"] = [_field_to_dict(f) for f in field.children]
        result["children_allow_extra"] = field.children_allow_extra
    if field.is_directory:
        result["is_directory"] = True

    return result


def _schema_to_list(schema: ConfigItems | None) -> list[dict[str, Any]]:
    """Serialize a ConfigItems to a JSON-friendly list."""
    if schema is None:
        return []
    return [_field_to_dict(f) for f in schema]


def _plugin_to_dict(plugin: PluginInfo) -> dict[str, Any]:
    """Serialize a PluginInfo to a JSON-friendly dict."""
    result: dict[str, Any] = {
        "name": plugin.name,
        "description": plugin.description,
        "environments": plugin.environments,
        "config_schema": _schema_to_list(plugin.config_schema),
    }

    # Special-case scratchpads: include the per-scratchpad child schema
    if plugin.name == "scratchpads":
        try:
            from ..plugins.scratchpads.schema import SCRATCHPAD_SCHEMA  # noqa: PLC0415

            result["child_schema"] = _schema_to_list(SCRATCHPAD_SCHEMA)
        except ImportError:
            pass

    return result


def get_plugins_schema() -> list[dict[str, Any]]:
    """Return schema info for all available plugins."""
    plugins = discover_plugins()
    return [_plugin_to_dict(p) for p in plugins]


# ---------------------------------------------------------------------------
#  Include-aware configuration loading
# ---------------------------------------------------------------------------


def get_config() -> dict[str, Any]:
    """Load and return the fully-merged config (main + includes)."""
    config_path = get_config_path()

    # Determine conf.d path from the main file's include list
    _, conf_d = _find_conf_d(config_path)

    # Recursively load & merge (matches daemon's _open_config behaviour)
    merged = load_config()

    return {
        "path": str(config_path),
        "conf_d": str(conf_d) if conf_d else None,
        "exists": config_path.exists(),
        "config": merged,
    }


# ---------------------------------------------------------------------------
#  Validation (unchanged — works on the merged dict)
# ---------------------------------------------------------------------------


def validate_config(config: dict[str, Any]) -> list[str]:
    """Validate a config dict against all known plugin schemas.

    Returns a list of error/warning strings (empty means valid).
    """
    errors: list[str] = []
    plugins = {p.name: p for p in discover_plugins()}

    enabled = config.get("pyprland", {}).get("plugins", [])
    for plugin_name in enabled:
        plugin_config = config.get(plugin_name, {})
        info = plugins.get(plugin_name)
        if not info or not info.config_schema:
            continue

        validator = ConfigValidator(plugin_config, plugin_name, _log)
        errors.extend(validator.validate(info.config_schema))
        errors.extend(validator.warn_unknown_keys(info.config_schema))

    if "scratchpads" in enabled:
        try:
            from ..plugins.scratchpads.schema import (  # noqa: PLC0415
                get_template_names,
                is_pure_template,
                validate_scratchpad_config,
            )

            scratch_section = config.get("scratchpads", {})
            template_names = get_template_names(scratch_section)
            for name, scratch_conf in scratch_section.items():
                if isinstance(scratch_conf, dict):
                    errors.extend(
                        validate_scratchpad_config(
                            name,
                            scratch_conf,
                            is_template=is_pure_template(name, scratch_section, template_names),
                        )
                    )
        except ImportError:
            pass

    return errors


# ---------------------------------------------------------------------------
#  TOML generation helpers
# ---------------------------------------------------------------------------

_BARE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _toml_key(key: str) -> str:
    """Quote a TOML key if it contains characters not allowed in bare keys."""
    if _BARE_KEY_RE.match(key):
        return key
    # Use double-quoted key with minimal escaping
    escaped = key.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _generate_plugin_toml(plugin_name: str, plugin_data: dict[str, Any]) -> str:
    """Generate a ``conf.d/<plugin>.toml`` file.

    Layout::

        [pyprland]
        plugins = ["<plugin_name>"]

        [<plugin_name>]
        key = value

        [<plugin_name>.<sub>]
        ...
    """
    lines: list[str] = [
        "# Managed by pypr-gui",
        f"# {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        "",
        "[pyprland]",
        f'plugins = ["{plugin_name}"]',
        "",
    ]

    # Separate simple values from sub-tables
    simple: dict[str, Any] = {}
    subs: dict[str, dict[str, Any]] = {}
    for key, value in plugin_data.items():
        if isinstance(value, dict):
            subs[key] = value
        else:
            simple[key] = value

    # Top-level plugin section (only if there are simple values)
    if simple:
        lines.append(f"[{plugin_name}]")
        for k, v in simple.items():
            lines.append(f"{_toml_key(k)} = {format_toml_value(v)}")
        lines.append("")

    # Sub-tables
    for sub_name, sub_data in subs.items():
        _write_subtable(lines, f"{plugin_name}.{_toml_key(sub_name)}", sub_data)

    return "\n".join(lines)


def _write_subtable(lines: list[str], prefix: str, data: dict[str, Any]) -> None:
    """Recursively write ``[prefix]`` and any nested sub-tables."""
    simple: dict[str, Any] = {}
    subs: dict[str, dict[str, Any]] = {}
    for k, v in data.items():
        if isinstance(v, dict):
            subs[k] = v
        else:
            simple[k] = v

    lines.append(f"[{prefix}]")
    for k, v in simple.items():
        lines.append(f"{_toml_key(k)} = {format_toml_value(v)}")
    lines.append("")

    for sub_name, sub_data in subs.items():
        _write_subtable(lines, f"{prefix}.{_toml_key(sub_name)}", sub_data)


def _generate_variables_toml(variables: dict[str, Any]) -> str:
    """Generate ``conf.d/variables.toml``."""
    lines: list[str] = [
        "# Managed by pypr-gui",
        f"# {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        "",
        "[pyprland.variables]",
    ]
    for k, v in variables.items():
        lines.append(f"{_toml_key(k)} = {format_toml_value(v)}")
    lines.append("")
    return "\n".join(lines)


def _generate_main_toml(
    pyprland_section: dict[str, Any],
    main_only_plugins: list[str],
    include_paths: list[str],
) -> str:
    """Generate the main ``config.toml``.

    Contains only ``[pyprland]`` with the option-less plugins, the include
    directive, and any other core pyprland keys (except ``variables`` which
    live in ``conf.d/variables.toml``).
    """
    lines: list[str] = [
        "# Pyprland configuration",
        "# Managed by pypr-gui",
        f"# {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        "",
        "[pyprland]",
    ]

    # Include directive first
    if include_paths:
        lines.append(f"include = {format_toml_value(include_paths)}")

    # Plugins list (only option-less plugins)
    if main_only_plugins:
        lines.append(f"plugins = {format_toml_value(sorted(set(main_only_plugins)))}")

    # Any remaining pyprland keys (except plugins, include, variables)
    skip = {"plugins", "include", "variables"}
    for k, v in pyprland_section.items():
        if k not in skip:
            lines.append(f"{_toml_key(k)} = {format_toml_value(v)}")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  Save with data-driven conf.d split
# ---------------------------------------------------------------------------


def _backup_conf_d_file(path: Path) -> Path | None:
    """Back up a conf.d file by renaming to ``.bak``."""
    if not path.exists():
        return None
    bak = path.with_suffix(".toml.bak")
    shutil.copy2(path, bak)
    _log.info("Backed up %s -> %s", path, bak)
    return bak


def _find_conf_d(config_path: Path) -> tuple[list[str], Path | None]:
    """Read the original main file and resolve the conf.d directory.

    Returns ``(include_paths, conf_d_path | None)``.
    """
    original_base = load_toml(config_path) if config_path.exists() else {}
    include_paths: list[str] = list(original_base.get("pyprland", {}).get("include", []))

    for raw in include_paths:
        resolved = resolve_config_path(raw)
        if resolved.is_dir():
            return include_paths, resolved

    return include_paths, None


def _write_confd_plugins(
    conf_d: Path,
    confd_plugins: dict[str, dict[str, Any]],
    existing_confd_files: dict[str, Path],
) -> set[str]:
    """Write ``conf.d/<plugin>.toml`` for each plugin with data.

    Also handles disabled plugins (clears their ``[pyprland] plugins`` list
    but preserves config) and backs up composite files.

    Returns the set of plugin names that were written.
    """
    known_stems = set(confd_plugins.keys()) | {"variables"}

    # Back up composite files whose stem doesn't match a known plugin
    for stem, path in existing_confd_files.items():
        if stem not in known_stems and path.exists():
            _backup_conf_d_file(path)

    # Write per-plugin files
    written: set[str] = set()
    for plugin_name, plugin_data in confd_plugins.items():
        content = _generate_plugin_toml(plugin_name, plugin_data)
        dest = conf_d / f"{plugin_name}.toml"
        dest.write_text(content, encoding="utf-8")
        written.add(plugin_name)
        _log.info("Wrote %s", dest)

    # Disabled plugins: clear their plugins list, keep config data
    for stem, path in existing_confd_files.items():
        if stem in written or stem == "variables" or not path.exists():
            continue
        existing = load_toml(path)
        if existing.get("pyprland", {}).get("plugins"):
            existing.setdefault("pyprland", {})["plugins"] = []
            path.write_text(_generate_plugin_toml_raw(existing), encoding="utf-8")
            _log.info("Disabled plugin in %s (config preserved)", path)

    return written


def _cleanup_composite_files(
    existing_confd_files: dict[str, Path],
    known_stems: set[str],
    written_files: set[str],
    has_variables: bool,
) -> None:
    """Remove fully-migrated composite conf.d files."""
    for stem, path in existing_confd_files.items():
        if stem in known_stems or stem in written_files or not path.exists():
            continue
        old_data = load_toml(path)
        old_plugin_names = old_data.get("pyprland", {}).get("plugins", [])
        all_migrated = all(p in written_files for p in old_plugin_names)
        old_has_vars = bool(old_data.get("pyprland", {}).get("variables"))
        if all_migrated and (not old_has_vars or has_variables):
            path.unlink()
            _log.info("Removed fully-migrated composite file %s", path)


def save_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate and save config, splitting across main file + conf.d/.

    Rules:
    * Plugins with config data → ``conf.d/<plugin>.toml``
    * Plugins without config data → listed in main ``config.toml``
    * ``pyprland.variables`` → ``conf.d/variables.toml``
    * Disabled plugins keep their conf.d file (config preserved) but are
      removed from the file's ``[pyprland] plugins`` list.
    """
    errors = validate_config(config)
    config_path = get_config_path()

    include_paths, conf_d = _find_conf_d(config_path)
    backup_path = backup_config(config_path)

    pyprland_section: dict[str, Any] = dict(config.get("pyprland", {}))
    all_enabled: list[str] = list(pyprland_section.get("plugins", []))
    variables: dict[str, Any] = dict(pyprland_section.get("variables", {}))

    # No conf.d: single-file mode
    if conf_d is None:
        content = generate_toml(config)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(content, encoding="utf-8")
        return _save_result(errors, config_path, backup_path)

    # conf.d mode: split config across files
    conf_d.mkdir(parents=True, exist_ok=True)

    # Classify: plugins with data → conf.d, rest → main config.toml
    main_only_plugins: list[str] = []
    confd_plugins: dict[str, dict[str, Any]] = {}
    for name in all_enabled:
        data = config.get(name, {})
        if isinstance(data, dict) and data:
            confd_plugins[name] = data
        else:
            main_only_plugins.append(name)

    existing_confd_files = {f.stem: f for f in conf_d.iterdir() if f.suffix == ".toml"} if conf_d.is_dir() else {}

    written = _write_confd_plugins(conf_d, confd_plugins, existing_confd_files)

    if variables:
        dest = conf_d / "variables.toml"
        dest.write_text(_generate_variables_toml(variables), encoding="utf-8")

    known_stems = set(confd_plugins.keys()) | {"variables"}
    _cleanup_composite_files(existing_confd_files, known_stems, written, bool(variables))

    main_content = _generate_main_toml(pyprland_section, main_only_plugins, include_paths)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(main_content, encoding="utf-8")

    return _save_result(errors, config_path, backup_path, conf_d)


def _save_result(
    errors: list[str],
    config_path: Path,
    backup_path: Path | None,
    conf_d: Path | None = None,
) -> dict[str, Any]:
    """Build the JSON-serialisable save response."""
    result: dict[str, Any] = {
        "ok": not errors,
        "errors": errors,
        "path": str(config_path),
        "backup": str(backup_path) if backup_path else None,
    }
    if conf_d is not None:
        result["conf_d"] = str(conf_d)
    return result


def _generate_plugin_toml_raw(existing_data: dict[str, Any]) -> str:
    """Re-serialize an existing conf.d file preserving its structure.

    Used when we only need to tweak the ``[pyprland] plugins`` list of an
    existing file (e.g. to disable a plugin while keeping its config).
    """
    lines: list[str] = [
        "# Managed by pypr-gui",
        f"# {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        "",
    ]

    # [pyprland] section
    pypr = existing_data.get("pyprland", {})
    lines.append("[pyprland]")
    plugin_list = pypr.get("plugins", [])
    if plugin_list:
        lines.append(f"plugins = {format_toml_value(plugin_list)}")
    else:
        lines.append("plugins = []")
    lines.append("")

    # Everything else
    for section_name, section_data in existing_data.items():
        if section_name == "pyprland" or not isinstance(section_data, dict):
            continue
        _write_subtable(lines, section_name, section_data)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  IPC
# ---------------------------------------------------------------------------


async def _send_ipc_command(command: str) -> str:
    """Send a command to the pyprland daemon via IPC.

    Returns the daemon's response string.
    """
    try:
        reader, writer = await asyncio.open_unix_connection(CONTROL)
        writer.write((command + "\n").encode())
        writer.write_eof()
        await writer.drain()
        response = (await reader.read()).decode("utf-8")
        writer.close()
        await writer.wait_closed()
    except (ConnectionRefusedError, FileNotFoundError):
        return "ERROR: pypr daemon is not running"
    else:
        return response


async def apply_config(config: dict[str, Any]) -> dict[str, Any]:
    """Save config and reload the running daemon."""
    result = save_config(config)

    # Attempt to reload the daemon
    response = await _send_ipc_command("reload")
    result["reload_response"] = response.strip()
    result["daemon_reloaded"] = not response.startswith("ERROR")

    return result
