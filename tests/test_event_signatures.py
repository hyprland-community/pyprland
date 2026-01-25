"""Validate event handler signatures match Protocol definitions.

This test ensures all event_* methods in plugins conform to the expected
signatures defined in the HyprlandEvents and NiriEvents Protocols.
"""

import importlib
import inspect
from typing import get_type_hints

import pytest

from pyprland.plugins.protocols import HyprlandEvents, NiriEvents


# Modules containing classes with event handlers
PLUGIN_MODULES = [
    "pyprland.plugins.pyprland.hyprland_core",
    "pyprland.plugins.pyprland.niri_core",
    "pyprland.plugins.monitors",
    "pyprland.plugins.scratchpads",
    "pyprland.plugins.layout_center",
    "pyprland.plugins.shift_monitors",
    "pyprland.plugins.workspaces_follow_focus",
    "pyprland.plugins.wallpapers",
    "pyprland.plugins.menubar",
    "pyprland.plugins.fcitx5_switcher",
]


def get_protocol_signatures(protocol_cls: type) -> dict[str, inspect.Signature]:
    """Extract method signatures from a Protocol class."""
    return {
        name: inspect.signature(getattr(protocol_cls, name))
        for name in dir(protocol_cls)
        if not name.startswith("_") and callable(getattr(protocol_cls, name))
    }


def signatures_compatible(actual: inspect.Signature, expected: inspect.Signature) -> tuple[bool, str]:
    """Check if actual signature is compatible with expected.

    Compatible means:
    - Same number of parameters (excluding self)
    - Parameters can accept the same types (checking defaults for optional params)

    Returns:
        Tuple of (is_compatible, error_message)
    """
    actual_params = list(actual.parameters.values())
    expected_params = list(expected.parameters.values())

    # Filter out 'self' parameter
    actual_params = [p for p in actual_params if p.name != "self"]
    expected_params = [p for p in expected_params if p.name != "self"]

    # Check parameter count compatibility
    # Actual can have defaults where expected requires a param, but not vice versa
    actual_required = sum(1 for p in actual_params if p.default is inspect.Parameter.empty)
    expected_required = sum(1 for p in expected_params if p.default is inspect.Parameter.empty)

    # The actual method must accept at least as many required params as expected
    # and the total param count should match
    if len(actual_params) != len(expected_params):
        return False, f"parameter count mismatch: expected {len(expected_params)}, got {len(actual_params)}"

    # For event handlers, the key check is that methods accepting an optional param
    # (with default) are compatible with being called with that param
    # The bug we're catching: method has 0 params but event passes 1
    if actual_required > expected_required:
        return False, f"requires {actual_required} params but event provides {expected_required}"

    return True, ""


def test_hyprland_event_signatures():
    """Verify all Hyprland event_* methods match Protocol signatures."""
    protocol_methods = get_protocol_signatures(HyprlandEvents)
    errors = []

    for module_name in PLUGIN_MODULES:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue

        for cls_name, cls in inspect.getmembers(module, inspect.isclass):
            # Skip imported classes (only check classes defined in this module)
            if cls.__module__ != module_name:
                continue

            for method_name in dir(cls):
                if not method_name.startswith("event_"):
                    continue

                if method_name not in protocol_methods:
                    # Event not in Protocol - that's OK, Protocol may not cover all events
                    continue

                method = getattr(cls, method_name)
                if not callable(method):
                    continue

                try:
                    actual_sig = inspect.signature(method)
                except (ValueError, TypeError):
                    continue

                expected_sig = protocol_methods[method_name]
                is_compatible, error_msg = signatures_compatible(actual_sig, expected_sig)

                if not is_compatible:
                    errors.append(
                        f"{module_name}:{cls_name}.{method_name}: {error_msg}\n  Expected: {expected_sig}\n  Got:      {actual_sig}"
                    )

    assert not errors, "Event handler signature mismatches:\n" + "\n\n".join(errors)


def test_niri_event_signatures():
    """Verify all Niri niri_* methods match Protocol signatures."""
    protocol_methods = get_protocol_signatures(NiriEvents)
    errors = []

    for module_name in PLUGIN_MODULES:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue

        for cls_name, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module_name:
                continue

            for method_name in dir(cls):
                if not method_name.startswith("niri_"):
                    continue

                if method_name not in protocol_methods:
                    continue

                method = getattr(cls, method_name)
                if not callable(method):
                    continue

                try:
                    actual_sig = inspect.signature(method)
                except (ValueError, TypeError):
                    continue

                expected_sig = protocol_methods[method_name]
                is_compatible, error_msg = signatures_compatible(actual_sig, expected_sig)

                if not is_compatible:
                    errors.append(
                        f"{module_name}:{cls_name}.{method_name}: {error_msg}\n  Expected: {expected_sig}\n  Got:      {actual_sig}"
                    )

    assert not errors, "Niri event handler signature mismatches:\n" + "\n\n".join(errors)


def test_protocol_methods_documented():
    """Ensure all Protocol methods have docstrings."""
    for protocol_cls in [HyprlandEvents, NiriEvents]:
        for name in dir(protocol_cls):
            if name.startswith("_"):
                continue
            method = getattr(protocol_cls, name)
            if callable(method):
                assert method.__doc__, f"{protocol_cls.__name__}.{name} missing docstring"
