"""Custom hatch build hook to compile the optional C client.

Attempts to compile client/pypr-client.c into a native binary.
If compilation fails (e.g., no C compiler available), the build
continues without the native client -- it is purely optional.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def _find_compiler() -> str:
    """Find a C compiler from CC env var or common names.

    Returns:
        The compiler command string, or empty string if none found.
    """
    import os  # noqa: PLC0415

    cc = os.environ.get("CC", "")
    if cc:
        return cc
    for candidate in ("cc", "gcc", "clang"):
        if shutil.which(candidate):
            return candidate
    return ""


def _try_compile(cc: str, source: Path) -> tuple[Path | None, str]:
    """Attempt to compile the C client.

    Args:
        cc: C compiler command.
        source: Path to the C source file.

    Returns:
        Tuple of (output_path or None, warning message if failed).
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="pypr-build-"))
    output = tmpdir / "pypr-client"
    cmd = [cc, "-O2", "-o", str(output), str(source)]

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
        """Compile the C client and include it in the wheel if successful."""
        if self.target_name != "wheel":
            return

        source = Path(self.root) / "client" / "pypr-client.c"
        if not source.exists():
            self.app.display_warning("C client source not found, skipping native client build")
            return

        cc = _find_compiler()
        if not cc:
            self.app.display_warning("No C compiler found (set CC env var or install gcc/clang). Skipping native pypr-client build.")
            return

        self.app.display_info(f"Compiling native client with {cc}")
        output, warning = _try_compile(cc, source)

        if output is None:
            self.app.display_warning(warning)
            return

        self.app.display_success("Native pypr-client compiled successfully")

        # Files in <package>.data/scripts/ are installed to the bin/ directory
        # by pip/uv, alongside Python entry points.
        build_data["force_include"][str(output)] = "pyprland.data/scripts/pypr-client"

        # Mark the wheel as platform-specific since it contains a native binary
        build_data["pure_python"] = False
        build_data["infer_tag"] = True
