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

HYPRLAND_INSTANCE_SIGNATURE = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "NO_INSTANCE")

MINIMUM_ADDR_LEN = 4  # Minimum length for address without "0x" prefix
MINIMUM_FULL_ADDR_LEN = 3  # Minimum length for full address with "0x" prefix (e.g., "0x1")

MAX_SOCKET_FILE_LEN = 15
MAX_SOCKET_PATH_LEN = 107

try:
    # May throw an OSError because AF_UNIX path is too long: try to work around it only if needed
    ORIGINAL_IPC_FOLDER = (
        f"{os.environ['XDG_RUNTIME_DIR']}/hypr/{HYPRLAND_INSTANCE_SIGNATURE}"
        if os.path.exists(f"{os.environ.get('XDG_RUNTIME_DIR', '')}/hypr/{HYPRLAND_INSTANCE_SIGNATURE}")
        else f"/tmp/hypr/{HYPRLAND_INSTANCE_SIGNATURE}"  # noqa: S108
    )

    if len(ORIGINAL_IPC_FOLDER) >= MAX_SOCKET_PATH_LEN - MAX_SOCKET_FILE_LEN:
        IPC_FOLDER = f"/tmp/.pypr-{HYPRLAND_INSTANCE_SIGNATURE}"  # noqa: S108
    else:
        IPC_FOLDER = ORIGINAL_IPC_FOLDER

    def init_ipc_folder() -> None:
        """Initialize the IPC folder."""
        if ORIGINAL_IPC_FOLDER != IPC_FOLDER and not os.path.exists(IPC_FOLDER):
            with contextlib.suppress(OSError):
                os.symlink(ORIGINAL_IPC_FOLDER, IPC_FOLDER)

except KeyError:
    print("This is a fatal error, assuming we are running documentation generation or testing in a sandbox, hence ignoring it")
    IPC_FOLDER = "/"

    def init_ipc_folder() -> None:
        """Initialize the IPC folder."""
