"""Custom hatch build hook to compile the optional native C client.

The ``pypr-client`` binary is a fast, dependency free drop in for the ``pypr``
command. Whether it gets compiled and bundled into the wheel depends on the
``PYPRLAND_BUILD_NATIVE`` environment variable:

- unset (the default): best effort build. When a C compiler is available the
  client is compiled (dynamically linked) and the wheel is tagged for the
  building platform. With no compiler the build quietly falls back to a pure
  python wheel. This is what source installs get (``pip`` or ``uv`` from an
  sdist or a git checkout). See issue #236.
- ``"1"``: force a statically linked binary in a wheel tagged
  ``manylinux_2_17_x86_64``, suitable for publishing to PyPI.
- ``"0"``: never compile, always produce a pure python wheel. Used to publish
  the cross platform PyPI wheel, and as an escape hatch.
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
        """Compile the C client and include it in the wheel if appropriate.

        Runs for every wheel build unless ``PYPRLAND_BUILD_NATIVE=0`` opts out.
        With ``PYPRLAND_BUILD_NATIVE=1`` the binary is statically linked and the
        wheel is tagged ``manylinux_2_17_x86_64`` for PyPI. Otherwise (the
        default, for example source installs) it is a best effort, dynamically
        linked build tagged for the running platform.
        """
        if self.target_name != "wheel":
            return

        mode = os.environ.get("PYPRLAND_BUILD_NATIVE", "")
        if mode == "0":  # explicit opt out, keep the wheel pure python
            return

        # PYPRLAND_BUILD_NATIVE=1 produces a portable, statically linked binary
        # for the published manylinux wheel. Any other value (including unset)
        # does a best effort dynamic build so that source installs still ship
        # the client (see issue #236).
        static = mode == "1"

        source = Path(self.root) / "client" / "pypr-client.c"
        if not source.exists():
            self.app.display_warning("C client source not found, skipping native client build")
            return

        cc = _find_compiler()
        if not cc:
            self.app.display_warning("No C compiler found (set CC env var or install gcc/clang). Skipping native pypr-client build.")
            return

        self.app.display_info(f"Compiling native client with {cc}" + (" (static)" if static else ""))
        output, warning = _try_compile(cc, source, static=static)

        if output is None:
            self.app.display_warning(warning)
            return

        self.app.display_success("Native pypr-client compiled successfully")

        # Use shared_scripts so hatchling generates the correct
        # {name}-{version}.data/scripts/ path in the wheel (PEP 427).
        build_data["shared_scripts"][str(output)] = "pypr-client"

        # The wheel now carries a native binary, so it is no longer pure python.
        build_data["pure_python"] = False
        if static:
            # Portable binary, tag explicitly so it can be uploaded to PyPI.
            build_data["tag"] = MANYLINUX_TAG
        else:
            # Built for this machine, let hatchling infer the platform tag.
            build_data["infer_tag"] = True
