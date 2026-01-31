"""Backend registry for online wallpaper sources.

This module provides the registry for wallpaper backends and re-exports
the base types for convenience.
"""

# Re-export base types for backward compatibility
from .base import (
    HTTP_OK,
    Backend,
    BackendError,
    ImageInfo,
    fetch_redirect_image,
)

__all__ = [
    "HTTP_OK",
    "Backend",
    "BackendError",
    "ImageInfo",
    "fetch_redirect_image",
    "get_available_backends",
    "get_backend",
    "register_backend",
]

# Backend registry - populated by imports below
BACKENDS: dict[str, type[Backend]] = {}


def register_backend(cls: type[Backend]) -> type[Backend]:
    """Decorator to register a backend class.

    Args:
        cls: Backend class to register.

    Returns:
        The same class, unmodified.
    """
    BACKENDS[cls.name] = cls
    return cls


def get_backend(name: str) -> Backend:
    """Get a backend instance by name.

    Args:
        name: Backend identifier.

    Returns:
        An instance of the requested backend.

    Raises:
        KeyError: If the backend is not registered.
    """
    if name not in BACKENDS:
        available = ", ".join(BACKENDS.keys())
        msg = f"Unknown backend '{name}'. Available: {available}"
        raise KeyError(msg)
    return BACKENDS[name]()


def get_available_backends() -> list[str]:
    """Get list of all registered backend names.

    Returns:
        List of backend names.
    """
    return list(BACKENDS.keys())


# Import backends to register them
# Cyclic import is intentional: backends import register_backend from here
# pylint: disable=wrong-import-position,cyclic-import
from . import bing, picsum, reddit, unsplash, wallhaven  # noqa: E402, F401
