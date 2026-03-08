import pytest

from pyprland.plugins.stash import Extension
from tests.conftest import make_extension


@pytest.fixture
def extension():
    return make_extension(Extension)


# -- run_stash: stashing --


@pytest.mark.asyncio
async def test_stash_moves_window_to_special_workspace(extension):
    """Stashing a normal window moves it to special:stash-default."""
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "workspace": {"id": 1, "name": "1"},
    }

    await extension.run_stash()

    extension.backend.move_window_to_workspace.assert_called_with("0xabc", "special:stash-default")


@pytest.mark.asyncio
async def test_stash_custom_name(extension):
    """Stashing with a custom name uses that name."""
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "workspace": {"id": 2, "name": "2"},
    }

    await extension.run_stash("work")

    extension.backend.move_window_to_workspace.assert_called_with("0xabc", "special:stash-work")


# -- run_stash: unstashing --


@pytest.mark.asyncio
async def test_unstash_moves_window_back(extension):
    """Unstashing a stashed window restores it to the active workspace."""
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "workspace": {"id": -99, "name": "special:stash-default"},
    }

    await extension.run_stash()

    extension.backend.execute.assert_called_with(
        [
            "togglespecialworkspace stash-default",
            f"movetoworkspacesilent {extension.state.active_workspace},address:0xabc",
            "focuswindow address:0xabc",
        ]
    )


@pytest.mark.asyncio
async def test_unstash_from_different_stash(extension):
    """A window in stash-work is unstashed even when called with default name."""
    extension.backend.execute_json.return_value = {
        "address": "0xdef",
        "workspace": {"id": -42, "name": "special:stash-work"},
    }

    # Called without arguments (name="default"), but window is in stash-work
    await extension.run_stash()

    extension.backend.execute.assert_called_with(
        [
            "togglespecialworkspace stash-work",
            f"movetoworkspacesilent {extension.state.active_workspace},address:0xdef",
            "focuswindow address:0xdef",
        ]
    )


# -- run_stash: edge cases --


@pytest.mark.asyncio
async def test_stash_no_active_window(extension):
    """No-op when there is no active window."""
    extension.backend.execute_json.return_value = {
        "address": "",
        "workspace": {"id": 0, "name": ""},
    }

    await extension.run_stash()

    extension.backend.move_window_to_workspace.assert_not_called()
    extension.backend.execute.assert_not_called()


# -- run_stash_show --


@pytest.mark.asyncio
async def test_stash_show_default(extension):
    """Toggling stash visibility with default name."""
    await extension.run_stash_show()

    extension.backend.execute.assert_called_with("togglespecialworkspace stash-default")


@pytest.mark.asyncio
async def test_stash_show_custom_name(extension):
    """Toggling stash visibility with a custom name."""
    await extension.run_stash_show("music")

    extension.backend.execute.assert_called_with("togglespecialworkspace stash-music")
