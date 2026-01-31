"""Built-in plugins for Pyprland.

This package contains all bundled plugins. Each plugin module exports an
Extension class that inherits from Plugin (pyprland.plugins.interface).
Plugins are loaded dynamically based on the 'plugins' list in config.
"""

__all__ = ["interface"]
