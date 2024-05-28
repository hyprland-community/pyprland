"""Utilities."""

__all__ = ["get_mount_point", "get_max_length"]

import os


def get_mount_point(path: str) -> str:
    """Return the mount point of the given path."""
    path = os.path.abspath(path)
    while path != "/":
        if os.path.ismount(path):
            return path
        path = os.path.dirname(path)
    return path  # root '/' is the mount point for the topmost directory


def get_max_length(path: str) -> int:
    """Return the maximum length of a path in the given path's filesystem."""
    return os.pathconf(get_mount_point(path), "PC_PATH_MAX")
