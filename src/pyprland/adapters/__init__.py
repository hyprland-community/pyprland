"""Backend adapters for compositor abstraction.

This package provides the EnvironmentBackend abstraction layer that allows
Pyprland to work with multiple compositors (Hyprland, Niri) and fallback
environments (generic Wayland via wlr-randr, X11 via xrandr).
"""

from .proxy import BackendProxy

__all__ = ["BackendProxy"]
