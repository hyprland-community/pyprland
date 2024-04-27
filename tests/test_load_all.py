import tomllib

import pytest
from pytest_asyncio import fixture


@fixture
async def load_all_config(monkeypatch):
    "external config"
    config = """
[pyprland]
plugins = [
    "expose",
    "fetch_client_menu",
    "layout_center",
    "lost_windows",
    "magnify",
    "monitors",
    "scratchpads",
    "shift_monitors",
    "shortcuts_menu",
    "toggle_dpms",
    "toggle_special",
    "workspaces_follow_focus",
]

"""
    monkeypatch.setattr("tomllib.load", lambda x: tomllib.loads(config))
    yield


@pytest.mark.usefixtures("load_all_config", "server_fixture")
@pytest.mark.asyncio
async def test_load_all(subprocess_shell_mock):
    assert True
