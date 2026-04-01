"""Custom hatch build hook to compile the optional C client.

When the PYPRLAND_BUILD_NATIVE environment variable is set to "1", compiles
client/pypr-client.c into a statically-linked native binary and includes it
in a platform-specific wheel tagged for manylinux_2_17_x86_64.

Without the env var the hook does nothing and the wheel stays pure-python.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

# The manylinux tag to use for the platform-specific wheel.
# 2.17 corresponds to glibc 2.17 (CentOS 7) — effectively all modern Linux.
# With static linking the binary has *no* glibc dependency, so this is safe.
MANYLINUX_TAG = "cp3-none-manylinux_2_17_x86_64"


def _find_compiler() -> str:
    """Find a C compiler from CC env var or common names.

    Returns:
        The compiler command string, or empty string if none found.
    """
    cc = os.environ.get("CC", "")
    if cc:
        return cc
    for candidate in ("cc", "gcc", "clang"):
        if shutil.which(candidate):
            return candidate
    return ""


def _try_compile(cc: str, source: Path, *, static: bool = False) -> tuple[Path | None, str]:
    """Attempt to compile the C client.

    Args:
        cc: C compiler command.
        source: Path to the C source file.
        static: Whether to produce a statically-linked binary.

    Returns:
        Tuple of (output_path or None, warning message if failed).
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="pypr-build-"))
    output = tmpdir / "pypr-client"
    cmd = [cc, "-O2"]
    if static:
        cmd.append("-static")
    cmd.extend(["-o", str(output), str(source)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)  # noqa: S603
    except FileNotFoundError:
        return None, f"C compiler '{cc}' not found. Skipping native client build."
    except subprocess.TimeoutExpired:
        return None, "C client compilation timed out. Skipping native client build."

    if result.returncode != 0:
        return None, (
            f"C client compilation failed (exit {result.returncode}). Skipping native client build.\nstderr: {result.stderr.strip()}"
        )

    if not output.exists():
        return None, "Compiled binary not found after build. Skipping native client."

    output.chmod(0o755)  # noqa: S103
    return output, ""


class NativeClientBuildHook(BuildHookInterface):
    """Build hook that compiles the native C client."""

    PLUGIN_NAME = "native-client"

    def initialize(self, version: str, build_data: dict) -> None:  # noqa: ARG002
        """Compile the C client and include it in the wheel if successful.

        Only runs when PYPRLAND_BUILD_NATIVE=1 is set and the build target
        is a wheel.  The resulting wheel is tagged as manylinux so it can be
        uploaded to PyPI.
        """
        if self.target_name != "wheel":
            return

        if os.environ.get("PYPRLAND_BUILD_NATIVE") != "1":
            return

        source = Path(self.root) / "client" / "pypr-client.c"
        if not source.exists():
            self.app.display_warning("C client source not found, skipping native client build")
            return

        cc = _find_compiler()
        if not cc:
            self.app.display_warning("No C compiler found (set CC env var or install gcc/clang). Skipping native pypr-client build.")
            return

        self.app.display_info(f"Compiling native client with {cc} (static)")
        output, warning = _try_compile(cc, source, static=True)

        if output is None:
            self.app.display_warning(warning)
            return

        self.app.display_success("Native pypr-client compiled successfully")

        # Use shared_scripts so hatchling generates the correct
        # {name}-{version}.data/scripts/ path in the wheel (PEP 427).
        build_data["shared_scripts"][str(output)] = "pypr-client"

        # Mark the wheel as platform-specific with an explicit manylinux tag.
        build_data["pure_python"] = False
        build_data["tag"] = MANYLINUX_TAG
