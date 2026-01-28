"""IPC path management and constants."""

import contextlib
import os

__all__ = [
    "HYPRLAND_INSTANCE_SIGNATURE",
    "IPC_FOLDER",
    "MINIMUM_ADDR_LEN",
    "MINIMUM_FULL_ADDR_LEN",
    "init_ipc_folder",
]

HYPRLAND_INSTANCE_SIGNATURE = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
NIRI_SOCKET = os.environ.get("NIRI_SOCKET")

MINIMUM_ADDR_LEN = 4  # Minimum length for address without "0x" prefix
MINIMUM_FULL_ADDR_LEN = 3  # Minimum length for full address with "0x" prefix (e.g., "0x1")

MAX_SOCKET_FILE_LEN = 15
MAX_SOCKET_PATH_LEN = 107

# Determine IPC_FOLDER based on environment priority: Hyprland > Niri > Standalone
_ORIGINAL_IPC_FOLDER: str | None = None

if HYPRLAND_INSTANCE_SIGNATURE:
    # Hyprland environment
    try:
        _ORIGINAL_IPC_FOLDER = (
            f"{os.environ['XDG_RUNTIME_DIR']}/hypr/{HYPRLAND_INSTANCE_SIGNATURE}"
            if os.path.exists(f"{os.environ.get('XDG_RUNTIME_DIR', '')}/hypr/{HYPRLAND_INSTANCE_SIGNATURE}")
            else f"/tmp/hypr/{HYPRLAND_INSTANCE_SIGNATURE}"  # noqa: S108
        )

        if len(_ORIGINAL_IPC_FOLDER) >= MAX_SOCKET_PATH_LEN - MAX_SOCKET_FILE_LEN:
            IPC_FOLDER = f"/tmp/.pypr-{HYPRLAND_INSTANCE_SIGNATURE}"  # noqa: S108
        else:
            IPC_FOLDER = _ORIGINAL_IPC_FOLDER

    except KeyError:
        # XDG_RUNTIME_DIR not set - use /tmp fallback
        IPC_FOLDER = f"/tmp/hypr/{HYPRLAND_INSTANCE_SIGNATURE}"  # noqa: S108
        _ORIGINAL_IPC_FOLDER = IPC_FOLDER

elif NIRI_SOCKET:
    # Niri environment - use parent directory of NIRI_SOCKET
    IPC_FOLDER = os.path.dirname(NIRI_SOCKET)

else:
    # Standalone fallback - no environment detected
    IPC_FOLDER = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))


def init_ipc_folder() -> None:
    """Initialize the IPC folder.

    For Hyprland with shortened paths, creates a symlink.
    For other cases, the folder should already exist or will be created by the daemon.
    """
    if HYPRLAND_INSTANCE_SIGNATURE and _ORIGINAL_IPC_FOLDER and _ORIGINAL_IPC_FOLDER != IPC_FOLDER:
        if not os.path.exists(IPC_FOLDER):
            with contextlib.suppress(OSError):
                os.symlink(_ORIGINAL_IPC_FOLDER, IPC_FOLDER)
