import pytest

from pyprland.plugins.stash import Extension
from tests.conftest import make_extension
from tests.testtools import get_executed_commands


@pytest.fixture
def extension():
    return make_extension(Extension, config={})


@pytest.fixture
def styled_extension():
    return make_extension(Extension, config={"style": ["border_color rgb(ec8800)", "border_size 3"]})


@pytest.fixture
def overlay_extension():
    return make_extension(Extension, config={"restore_floating": False})


# -- run_stash: stashing --


@pytest.mark.asyncio
async def test_stash_moves_window_to_special_workspace(extension):
    """Stashing a tiled window moves it to special:st-default and makes it floating."""
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": False,
        "workspace": {"id": 1, "name": "1"},
    }

    await extension.run_stash()

    extension.backend.move_window_to_workspace.assert_called_with("0xabc", "special:st-default", silent=True)
    extension.backend.toggle_floating.assert_called_once_with("0xabc")
    assert extension._was_floating["0xabc"] is False


@pytest.mark.asyncio
async def test_stash_custom_name(extension):
    """Stashing with a custom name uses that name."""
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": False,
        "workspace": {"id": 2, "name": "2"},
    }

    await extension.run_stash("work")

    extension.backend.move_window_to_workspace.assert_called_with("0xabc", "special:st-work", silent=True)


@pytest.mark.asyncio
async def test_stash_already_floating_no_toggle(extension):
    """Stashing an already-floating window does not toggle floating."""
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": True,
        "workspace": {"id": 1, "name": "1"},
    }

    await extension.run_stash()

    extension.backend.move_window_to_workspace.assert_called_with("0xabc", "special:st-default", silent=True)
    extension.backend.toggle_floating.assert_not_called()
    assert extension._was_floating["0xabc"] is True


# -- run_stash: unstashing --


@pytest.mark.asyncio
async def test_unstash_moves_window_back(extension):
    """Unstashing a stashed tiled window restores it to the active workspace and restores tiled state."""
    extension._was_floating["0xabc"] = False
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "workspace": {"id": -99, "name": "special:st-default"},
    }

    await extension.run_stash()

    extension.backend.move_window_to_workspace.assert_called_with("0xabc", extension.state.active_workspace, silent=True)
    extension.backend.focus_window.assert_called_with("0xabc")
    extension.backend.toggle_floating.assert_called_once_with("0xabc")
    assert "0xabc" not in extension._was_floating


@pytest.mark.asyncio
async def test_unstash_from_different_stash(extension):
    """A window in stash-work is unstashed even when called with default name."""
    extension._was_floating["0xdef"] = False
    extension.backend.execute_json.return_value = {
        "address": "0xdef",
        "workspace": {"id": -42, "name": "special:st-work"},
    }

    # Called without arguments (name="default"), but window is in stash-work
    await extension.run_stash()

    extension.backend.move_window_to_workspace.assert_called_with("0xdef", extension.state.active_workspace, silent=True)
    extension.backend.focus_window.assert_called_with("0xdef")


@pytest.mark.asyncio
async def test_unstash_originally_floating_stays_floating(extension):
    """Unstashing a window that was originally floating does not toggle floating."""
    extension._was_floating["0xabc"] = True
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "workspace": {"id": -99, "name": "special:st-default"},
    }

    await extension.run_stash()

    extension.backend.toggle_floating.assert_not_called()
    assert "0xabc" not in extension._was_floating


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
    assert get_executed_commands(extension.backend.execute) == []


@pytest.mark.asyncio
async def test_stash_on_shown_window_removes_from_stash(extension):
    """Calling stash on a shown window removes it from the stash without re-toggling floating.

    With restore_floating=True (default), the window was already restored to
    tiled by _show_stash, so no additional toggle is needed.
    """
    extension._was_floating["0xaaa"] = False
    extension._was_floating["0xbbb"] = False
    extension.get_clients.return_value = [
        {"address": "0xaaa"},
        {"address": "0xbbb"},
    ]
    await extension.run_stash_toggle()  # show both
    extension.backend.reset_mock()

    # User focuses 0xaaa and calls stash
    extension.backend.execute_json.return_value = {
        "address": "0xaaa",
        "workspace": {"id": 1, "name": "1"},
    }

    await extension.run_stash()

    # Window stays on the active workspace — no move commands
    extension.backend.move_window_to_workspace.assert_not_called()
    # Floating was already restored by _show_stash — no toggle after removal
    extension.backend.toggle_floating.assert_not_called()
    # Removed from tracking, but stash is still visible (0xbbb remains)
    assert "0xaaa" not in extension._shown_addresses["default"]
    assert "0xbbb" in extension._shown_addresses["default"]
    assert extension._visible["default"] is True
    assert "0xaaa" not in extension._was_floating


@pytest.mark.asyncio
async def test_stash_on_shown_window_originally_floating_no_toggle(extension):
    """Removing a shown window that was originally floating does not toggle floating."""
    extension._was_floating["0xaaa"] = True
    extension.get_clients.return_value = [
        {"address": "0xaaa"},
    ]
    await extension.run_stash_toggle()  # show
    extension.backend.reset_mock()

    extension.backend.execute_json.return_value = {
        "address": "0xaaa",
        "workspace": {"id": 1, "name": "1"},
    }

    await extension.run_stash()

    extension.backend.toggle_floating.assert_not_called()
    assert "0xaaa" not in extension._was_floating


@pytest.mark.asyncio
async def test_stash_on_last_shown_window_clears_visibility(extension):
    """Removing the last shown window also clears the stash visibility state."""
    extension._was_floating["0xaaa"] = False
    extension.get_clients.return_value = [
        {"address": "0xaaa"},
    ]
    await extension.run_stash_toggle()  # show
    extension.backend.reset_mock()

    extension.backend.execute_json.return_value = {
        "address": "0xaaa",
        "workspace": {"id": 1, "name": "1"},
    }

    await extension.run_stash()

    extension.backend.move_window_to_workspace.assert_not_called()
    assert extension._visible.get("default", False) is False
    assert "default" not in extension._shown_addresses


# -- run_stash_toggle --


@pytest.mark.asyncio
async def test_stash_toggle_show_moves_windows_to_active_workspace(extension):
    """Showing a stash moves windows from the special workspace to the active workspace."""
    extension.get_clients.return_value = [
        {"address": "0xaaa"},
        {"address": "0xbbb"},
    ]

    await extension.run_stash_toggle()

    extension.get_clients.assert_called_with(workspace="special:st-default")
    extension.backend.move_window_to_workspace.assert_any_call("0xaaa", "1", silent=True)
    extension.backend.move_window_to_workspace.assert_any_call("0xbbb", "1", silent=True)


@pytest.mark.asyncio
async def test_stash_toggle_show_all_moves_are_silent(extension):
    """All window moves use movetoworkspacesilent."""
    extension.get_clients.return_value = [
        {"address": "0xaaa"},
        {"address": "0xbbb"},
    ]

    await extension.run_stash_toggle()

    calls = extension.backend.move_window_to_workspace.call_args_list
    assert calls[0].args == ("0xaaa", "1")
    assert calls[0].kwargs == {"silent": True}
    assert calls[1].args == ("0xbbb", "1")
    assert calls[1].kwargs == {"silent": True}
    extension.backend.focus_window.assert_not_called()


@pytest.mark.asyncio
async def test_stash_toggle_show_does_not_toggle_floating_for_untracked_windows(extension):
    """Showing a stash does not toggle floating for windows without tracked floating state.

    Windows not in _was_floating default to 'was floating', so no toggle occurs.
    """
    extension.get_clients.return_value = [
        {"address": "0xaaa"},
    ]

    await extension.run_stash_toggle()

    extension.backend.toggle_floating.assert_not_called()


@pytest.mark.asyncio
async def test_stash_toggle_show_no_windows_is_noop(extension):
    """Showing an empty stash does nothing."""
    extension.get_clients.return_value = []

    await extension.run_stash_toggle()

    extension.backend.move_window_to_workspace.assert_not_called()


@pytest.mark.asyncio
async def test_stash_toggle_show_custom_name(extension):
    """Showing a custom-named stash queries the right workspace."""
    extension.get_clients.return_value = [
        {"address": "0xaaa"},
    ]

    await extension.run_stash_toggle("music")

    extension.get_clients.assert_called_with(workspace="special:st-music")
    extension.backend.move_window_to_workspace.assert_called_with("0xaaa", "1", silent=True)


@pytest.mark.asyncio
async def test_stash_toggle_hide_moves_windows_back(extension):
    """Hiding a shown stash moves tracked windows back to the special workspace."""
    extension.get_clients.return_value = [
        {"address": "0xaaa"},
        {"address": "0xbbb"},
    ]

    # Show first
    await extension.run_stash_toggle()
    extension.backend.reset_mock()

    # Then hide
    await extension.run_stash_toggle()

    extension.backend.move_window_to_workspace.assert_any_call("0xaaa", "special:st-default")
    extension.backend.move_window_to_workspace.assert_any_call("0xbbb", "special:st-default")


@pytest.mark.asyncio
async def test_stash_toggle_hide_clears_tracking(extension):
    """After hiding, the stash is no longer considered visible."""
    extension.get_clients.return_value = [
        {"address": "0xaaa"},
    ]

    await extension.run_stash_toggle()  # show
    assert extension._visible["default"] is True

    await extension.run_stash_toggle()  # hide
    assert extension._visible["default"] is False
    assert "default" not in extension._shown_addresses


# -- style tagging --


@pytest.mark.asyncio
async def test_on_reload_clears_old_rules_and_registers_new(styled_extension):
    """on_reload clears old rules then registers tag-matched window rules."""
    await styled_extension.on_reload()

    commands = get_executed_commands(styled_extension.backend.execute)
    assert ("windowrule tag -stashed", {"base_command": "keyword"}) in commands
    assert ("windowrule border_color rgb(ec8800), match:tag stashed", {"base_command": "keyword"}) in commands
    assert ("windowrule border_size 3, match:tag stashed", {"base_command": "keyword"}) in commands


@pytest.mark.asyncio
async def test_on_reload_clears_rules_even_when_style_empty(extension):
    """on_reload clears old rules even when style config is empty."""
    await extension.on_reload()

    commands = get_executed_commands(extension.backend.execute)
    assert commands == [("windowrule tag -stashed", {"base_command": "keyword"})]


@pytest.mark.asyncio
async def test_stash_tags_window_when_style_configured(styled_extension):
    """Stashing a window tags it when style is configured."""
    styled_extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": True,
        "workspace": {"id": 1, "name": "1"},
    }

    await styled_extension.run_stash()

    commands = get_executed_commands(styled_extension.backend.execute)
    assert commands == [("tagwindow +stashed address:0xabc", {})]


@pytest.mark.asyncio
async def test_stash_does_not_tag_without_style(extension):
    """Stashing a window does not tag it when style is empty."""
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": True,
        "workspace": {"id": 1, "name": "1"},
    }

    await extension.run_stash()

    commands = get_executed_commands(extension.backend.execute)
    assert all("tagwindow" not in cmd for cmd, _ in commands)


@pytest.mark.asyncio
async def test_unstash_untags_window_when_style_configured(styled_extension):
    """Unstashing a window from special workspace untags it."""
    styled_extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "workspace": {"id": -99, "name": "special:st-default"},
    }

    await styled_extension.run_stash()

    commands = get_executed_commands(styled_extension.backend.execute)
    assert commands == [("tagwindow -stashed address:0xabc", {})]


@pytest.mark.asyncio
async def test_stash_on_shown_window_untags_when_style_configured(styled_extension):
    """Calling stash on a shown window untags it when style is configured."""
    styled_extension._was_floating["0xaaa"] = True
    styled_extension.get_clients.return_value = [
        {"address": "0xaaa"},
    ]
    await styled_extension.run_stash_toggle()  # show
    styled_extension.backend.reset_mock()

    styled_extension.backend.execute_json.return_value = {
        "address": "0xaaa",
        "workspace": {"id": 1, "name": "1"},
    }

    await styled_extension.run_stash()

    commands = get_executed_commands(styled_extension.backend.execute)
    assert commands == [("tagwindow -stashed address:0xaaa", {})]


# -- event_closewindow --


@pytest.mark.asyncio
async def test_closewindow_removes_from_was_floating(extension):
    """Closing a stashed window removes it from floating state tracking."""
    extension._was_floating["0xabc"] = False

    await extension.event_closewindow("abc")

    assert "0xabc" not in extension._was_floating


@pytest.mark.asyncio
async def test_closewindow_removes_from_shown_addresses(extension):
    """Closing a shown window removes it from the group but keeps the group alive."""
    extension._shown_addresses["default"] = ["0xaaa", "0xbbb"]
    extension._visible["default"] = True

    await extension.event_closewindow("aaa")

    assert "0xaaa" not in extension._shown_addresses["default"]
    assert "0xbbb" in extension._shown_addresses["default"]
    assert extension._visible["default"] is True


@pytest.mark.asyncio
async def test_closewindow_clears_group_when_last_shown_window_closed(extension):
    """Closing the last shown window in a group clears the group and visibility."""
    extension._shown_addresses["default"] = ["0xaaa"]
    extension._visible["default"] = True

    await extension.event_closewindow("aaa")

    assert "default" not in extension._shown_addresses
    assert extension._visible["default"] is False


@pytest.mark.asyncio
async def test_closewindow_noop_for_unknown_window(extension):
    """Closing an untracked window does not error or change state."""
    extension._was_floating["0xother"] = True
    extension._shown_addresses["default"] = ["0xother"]
    extension._visible["default"] = True

    await extension.event_closewindow("unknown")

    assert extension._was_floating == {"0xother": True}
    assert extension._shown_addresses == {"default": ["0xother"]}
    assert extension._visible["default"] is True


@pytest.mark.asyncio
async def test_closewindow_cleans_both_was_floating_and_shown(extension):
    """Closing a shown window cleans up both _was_floating and _shown_addresses."""
    extension._was_floating["0xaaa"] = False
    extension._shown_addresses["default"] = ["0xaaa"]
    extension._visible["default"] = True

    await extension.event_closewindow("aaa")

    assert "0xaaa" not in extension._was_floating
    assert "default" not in extension._shown_addresses
    assert extension._visible["default"] is False


# -- restore_floating=True (default): stash_toggle restores tiling --


@pytest.mark.asyncio
async def test_stash_toggle_show_restores_tiled_windows(extension):
    """With restore_floating=True, showing a stash toggles originally-tiled windows back to tiled."""
    extension._was_floating["0xaaa"] = False
    extension._was_floating["0xbbb"] = True
    extension.get_clients.return_value = [
        {"address": "0xaaa"},
        {"address": "0xbbb"},
    ]

    await extension.run_stash_toggle()

    # 0xaaa was tiled → toggled back to tiled
    extension.backend.toggle_floating.assert_called_once_with("0xaaa")
    # 0xbbb was floating → stays floating, no toggle


@pytest.mark.asyncio
async def test_stash_toggle_hide_refloats_tiled_windows(extension):
    """With restore_floating=True, hiding re-floats originally-tiled windows before moving back."""
    extension._was_floating["0xaaa"] = False
    extension._was_floating["0xbbb"] = True
    extension.get_clients.return_value = [
        {"address": "0xaaa"},
        {"address": "0xbbb"},
    ]

    await extension.run_stash_toggle()  # show
    extension.backend.reset_mock()

    await extension.run_stash_toggle()  # hide

    # 0xaaa was restored to tiled → re-floated before moving back
    extension.backend.toggle_floating.assert_called_once_with("0xaaa")
    # Both moved back to special workspace
    extension.backend.move_window_to_workspace.assert_any_call("0xaaa", "special:st-default")
    extension.backend.move_window_to_workspace.assert_any_call("0xbbb", "special:st-default")


@pytest.mark.asyncio
async def test_stash_toggle_show_hide_cycle_preserves_was_floating(extension):
    """A show/hide cycle preserves _was_floating so the next toggle still works."""
    extension._was_floating["0xaaa"] = False
    extension.get_clients.return_value = [
        {"address": "0xaaa"},
    ]

    # First cycle
    await extension.run_stash_toggle()  # show
    await extension.run_stash_toggle()  # hide
    extension.backend.reset_mock()

    # Second cycle — _was_floating should still have the entry
    await extension.run_stash_toggle()  # show again

    # Should still toggle floating for the tiled window
    extension.backend.toggle_floating.assert_called_once_with("0xaaa")
    assert extension._was_floating["0xaaa"] is False


@pytest.mark.asyncio
async def test_stash_on_shown_tiled_window_clears_tracking(extension):
    """Calling stash on a shown tiled window (with restore_floating=True) clears tracking cleanly."""
    extension._was_floating["0xaaa"] = False
    extension.get_clients.return_value = [
        {"address": "0xaaa"},
    ]
    await extension.run_stash_toggle()  # show — restores to tiled
    extension.backend.reset_mock()

    extension.backend.execute_json.return_value = {
        "address": "0xaaa",
        "workspace": {"id": 1, "name": "1"},
    }

    await extension.run_stash()

    # No toggle (already restored to tiled by _show_stash)
    extension.backend.toggle_floating.assert_not_called()
    # Tracking fully cleared
    assert "0xaaa" not in extension._was_floating
    assert extension._visible.get("default", False) is False


# -- restore_floating=False (overlay mode): stash_toggle keeps floating --


@pytest.mark.asyncio
async def test_overlay_show_does_not_toggle_floating(overlay_extension):
    """With restore_floating=False, showing does not toggle floating for tiled windows."""
    overlay_extension._was_floating["0xaaa"] = False
    overlay_extension.get_clients.return_value = [
        {"address": "0xaaa"},
    ]

    await overlay_extension.run_stash_toggle()

    overlay_extension.backend.toggle_floating.assert_not_called()


@pytest.mark.asyncio
async def test_overlay_hide_does_not_toggle_floating(overlay_extension):
    """With restore_floating=False, hiding does not toggle floating before moving back."""
    overlay_extension._was_floating["0xaaa"] = False
    overlay_extension.get_clients.return_value = [
        {"address": "0xaaa"},
    ]

    await overlay_extension.run_stash_toggle()  # show
    overlay_extension.backend.reset_mock()

    await overlay_extension.run_stash_toggle()  # hide

    overlay_extension.backend.toggle_floating.assert_not_called()
    overlay_extension.backend.move_window_to_workspace.assert_called_with("0xaaa", "special:st-default")


@pytest.mark.asyncio
async def test_overlay_stash_on_shown_tiled_window_restores_tiling(overlay_extension):
    """With restore_floating=False, calling stash on a shown tiled window toggles it back to tiled.

    In overlay mode, _show_stash does not restore tiling. So when the user calls
    stash to permanently remove the window from the stash, _restore_floating
    (already_restored=False) toggles it back.
    """
    overlay_extension._was_floating["0xaaa"] = False
    overlay_extension.get_clients.return_value = [
        {"address": "0xaaa"},
    ]
    await overlay_extension.run_stash_toggle()  # show — stays floating
    overlay_extension.backend.reset_mock()

    overlay_extension.backend.execute_json.return_value = {
        "address": "0xaaa",
        "workspace": {"id": 1, "name": "1"},
    }

    await overlay_extension.run_stash()

    # Restores tiling since it wasn't restored by _show_stash
    overlay_extension.backend.toggle_floating.assert_called_once_with("0xaaa")
    assert "0xaaa" not in overlay_extension._was_floating


@pytest.mark.asyncio
async def test_overlay_stash_on_shown_floating_window_no_toggle(overlay_extension):
    """With restore_floating=False, calling stash on a shown floating window does not toggle."""
    overlay_extension._was_floating["0xaaa"] = True
    overlay_extension.get_clients.return_value = [
        {"address": "0xaaa"},
    ]
    await overlay_extension.run_stash_toggle()  # show
    overlay_extension.backend.reset_mock()

    overlay_extension.backend.execute_json.return_value = {
        "address": "0xaaa",
        "workspace": {"id": 1, "name": "1"},
    }

    await overlay_extension.run_stash()

    overlay_extension.backend.toggle_floating.assert_not_called()
    assert "0xaaa" not in overlay_extension._was_floating
