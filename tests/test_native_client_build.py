"""Tests for the native ``pypr-client`` build hook (``hatch_build.py``).

Regression coverage for issue #236: a plain wheel build (what ``pip`` or ``uv``
do when installing from an sdist or a git checkout) must still bundle
``pypr-client`` when a C compiler is available, instead of quietly producing a
pure python wheel. Only ``PYPRLAND_BUILD_NATIVE=0`` should opt out.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

# hatch_build.py lives at the repository root, next to pyproject.toml.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _ensure_hatchling_importable() -> None:
    """Let hatch_build import even when the build backend isn't installed.

    ``hatchling`` is only a build-system requirement (installed in isolated
    build environments), so it is usually absent from the test venv. The hook
    only needs ``BuildHookInterface`` as a base class, so stub the module chain
    when the real one is unavailable.
    """
    path = "hatchling.builders.hooks.plugin.interface"
    try:
        __import__(path)
        return
    except ModuleNotFoundError:
        pass

    parts = path.split(".")
    for i in range(1, len(parts) + 1):
        name = ".".join(parts[:i])
        module = sys.modules.get(name)
        if module is None:
            module = types.ModuleType(name)
            sys.modules[name] = module
        if i < len(parts):
            module.__path__ = []
    sys.modules[path].BuildHookInterface = type("BuildHookInterface", (), {})


_ensure_hatchling_importable()

import hatch_build  # noqa: E402


class _FakeApp:
    """Stand-in for hatchling's build app, recording display calls."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def display_info(self, msg: str) -> None:
        self.messages.append(("info", msg))

    def display_warning(self, msg: str) -> None:
        self.messages.append(("warning", msg))

    def display_success(self, msg: str) -> None:
        self.messages.append(("success", msg))


def _make_hook() -> hatch_build.NativeClientBuildHook:
    """Build a hook instance without invoking hatchling's real __init__."""
    hook = hatch_build.NativeClientBuildHook.__new__(hatch_build.NativeClientBuildHook)
    hook.root = str(ROOT)
    hook.target_name = "wheel"
    hook.app = _FakeApp()
    return hook


def _run(monkeypatch, env_value: str | None) -> dict:
    """Run the hook with PYPRLAND_BUILD_NATIVE set to env_value (None=unset)."""
    if env_value is None:
        monkeypatch.delenv("PYPRLAND_BUILD_NATIVE", raising=False)
    else:
        monkeypatch.setenv("PYPRLAND_BUILD_NATIVE", env_value)
    build_data: dict = {"shared_scripts": {}}
    _make_hook().initialize("0", build_data)
    return build_data


def _has_compiler() -> bool:
    return bool(hatch_build._find_compiler())


def _scripts(build_data: dict) -> dict:
    return build_data["shared_scripts"]


def test_client_source_is_present() -> None:
    """The C source the hook compiles must ship in the tree."""
    assert (ROOT / "client" / "pypr-client.c").exists()


def test_default_build_bundles_client(monkeypatch) -> None:
    """Regression #236: an unset env var must still build the client.

    Before the fix the client was opt-in (PYPRLAND_BUILD_NATIVE=1), so plain
    source installs shipped a pure-python wheel with no pypr-client.
    """
    if not _has_compiler():
        pytest.skip("no C compiler available")

    build_data = _run(monkeypatch, None)
    scripts = _scripts(build_data)

    assert "pypr-client" in scripts.values(), "default build dropped pypr-client"
    assert build_data.get("pure_python") is False
    # A locally-built (non-portable) binary is tagged for this machine, not manylinux.
    assert build_data.get("infer_tag") is True
    assert "tag" not in build_data

    (compiled,) = [Path(p) for p, name in scripts.items() if name == "pypr-client"]
    assert compiled.exists() and compiled.stat().st_size > 0


def test_opt_out_keeps_wheel_pure(monkeypatch) -> None:
    """PYPRLAND_BUILD_NATIVE=0 must skip compilation entirely."""
    build_data = _run(monkeypatch, "0")
    assert _scripts(build_data) == {}
    assert "pure_python" not in build_data
    assert "tag" not in build_data
    assert "infer_tag" not in build_data


def test_native_build_tags_manylinux(monkeypatch) -> None:
    """PYPRLAND_BUILD_NATIVE=1 must produce a manylinux-tagged wheel."""
    if not _has_compiler():
        pytest.skip("no C compiler available")

    # A static build needs a static libc, which isn't present everywhere;
    # only assert the tagging contract when it can actually link.
    source = ROOT / "client" / "pypr-client.c"
    probe, _warning = hatch_build._try_compile(hatch_build._find_compiler(), source, static=True)
    if probe is None:
        pytest.skip("static linking unavailable on this system")

    build_data = _run(monkeypatch, "1")
    assert "pypr-client" in _scripts(build_data).values()
    assert build_data.get("pure_python") is False
    assert build_data.get("tag") == hatch_build.MANYLINUX_TAG
    assert "infer_tag" not in build_data


def test_non_wheel_target_is_noop(monkeypatch) -> None:
    """The hook must do nothing for non-wheel targets (e.g. sdist)."""
    monkeypatch.delenv("PYPRLAND_BUILD_NATIVE", raising=False)
    hook = _make_hook()
    hook.target_name = "sdist"
    build_data: dict = {"shared_scripts": {}}
    hook.initialize("0", build_data)
    assert _scripts(build_data) == {}
