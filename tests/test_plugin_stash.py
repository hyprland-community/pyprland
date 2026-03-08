import pytest

from pyprland.plugins.stash import Extension
from tests.conftest import make_extension


@pytest.fixture
def extension():
    return make_extension(Extension)


@pytest.fixture
def styled_extension():
    return make_extension(Extension, config={"style": ["border_color rgb(ec8800)", "border_size 3"]})


# -- run_stash: stashing --


@pytest.mark.asyncio
async def test_stash_moves_window_to_special_workspace(extension):
    """Stashing a tiled window moves it to special:stash-default and makes it floating."""
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": False,
        "workspace": {"id": 1, "name": "1"},
    }

    await extension.run_stash()

    extension.backend.move_window_to_workspace.assert_called_with("0xabc", "special:stash-default")
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

    extension.backend.move_window_to_workspace.assert_called_with("0xabc", "special:stash-work")


@pytest.mark.asyncio
async def test_stash_already_floating_no_toggle(extension):
    """Stashing an already-floating window does not toggle floating."""
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": True,
        "workspace": {"id": 1, "name": "1"},
    }

    await extension.run_stash()

    extension.backend.move_window_to_workspace.assert_called_with("0xabc", "special:stash-default")
    extension.backend.toggle_floating.assert_not_called()
    assert extension._was_floating["0xabc"] is True


# -- run_stash: unstashing --


@pytest.mark.asyncio
async def test_unstash_moves_window_back(extension):
    """Unstashing a stashed tiled window restores it to the active workspace and restores tiled state."""
    extension._was_floating["0xabc"] = False
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "workspace": {"id": -99, "name": "special:stash-default"},
    }

    await extension.run_stash()

    extension.backend.move_window_to_workspace.assert_called_with("0xabc", extension.state.active_workspace)
    extension.backend.focus_window.assert_called_with("0xabc")
    extension.backend.toggle_floating.assert_called_once_with("0xabc")
    assert "0xabc" not in extension._was_floating


@pytest.mark.asyncio
async def test_unstash_from_different_stash(extension):
    """A window in stash-work is unstashed even when called with default name."""
    extension._was_floating["0xdef"] = False
    extension.backend.execute_json.return_value = {
        "address": "0xdef",
        "workspace": {"id": -42, "name": "special:stash-work"},
    }

    # Called without arguments (name="default"), but window is in stash-work
    await extension.run_stash()

    extension.backend.move_window_to_workspace.assert_called_with("0xdef", extension.state.active_workspace)
    extension.backend.focus_window.assert_called_with("0xdef")


@pytest.mark.asyncio
async def test_unstash_originally_floating_stays_floating(extension):
    """Unstashing a window that was originally floating does not toggle floating."""
    extension._was_floating["0xabc"] = True
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "workspace": {"id": -99, "name": "special:stash-default"},
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
    extension.backend.execute.assert_not_called()


@pytest.mark.asyncio
async def test_stash_on_shown_window_removes_from_stash(extension):
    """Calling stash on a shown window removes it from the stash and restores tiled state."""
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
    # Floating was restored (was originally tiled)
    extension.backend.toggle_floating.assert_called_once_with("0xaaa")
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

    extension.get_clients.assert_called_with(workspace="special:stash-default")
    extension.backend.move_window_to_workspace.assert_any_call("0xaaa", "1", silent=True)
    extension.backend.move_window_to_workspace.assert_any_call("0xbbb", "1", silent=False)


@pytest.mark.asyncio
async def test_stash_toggle_show_last_move_is_not_silent(extension):
    """The last window move uses movetoworkspace (not silent) so Hyprland focuses it."""
    extension.get_clients.return_value = [
        {"address": "0xaaa"},
        {"address": "0xbbb"},
    ]

    await extension.run_stash_toggle()

    calls = extension.backend.move_window_to_workspace.call_args_list
    assert calls[0].args == ("0xaaa", "1")
    assert calls[0].kwargs == {"silent": True}
    assert calls[1].args == ("0xbbb", "1")
    assert calls[1].kwargs == {"silent": False}
    extension.backend.focus_window.assert_not_called()


@pytest.mark.asyncio
async def test_stash_toggle_show_does_not_toggle_floating(extension):
    """Showing a stash does not toggle floating — floating is set at stash time."""
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

    extension.get_clients.assert_called_with(workspace="special:stash-music")
    extension.backend.move_window_to_workspace.assert_called_with("0xaaa", "1", silent=False)


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

    extension.backend.move_window_to_workspace.assert_any_call("0xaaa", "special:stash-default")
    extension.backend.move_window_to_workspace.assert_any_call("0xbbb", "special:stash-default")


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

    styled_extension.backend.execute.assert_any_call(
        [
            "windowrule unset, match:tag stash",
            "windowrule tag -stash",
        ],
        base_command="keyword",
    )
    styled_extension.backend.execute.assert_any_call(
        [
            "windowrule border_color rgb(ec8800), match:tag stash",
            "windowrule border_size 3, match:tag stash",
        ],
        base_command="keyword",
    )


@pytest.mark.asyncio
async def test_on_reload_clears_rules_even_when_style_empty(extension):
    """on_reload clears old rules even when style config is empty."""
    await extension.on_reload()

    extension.backend.execute.assert_called_once_with(
        [
            "windowrule unset, match:tag stash",
            "windowrule tag -stash",
        ],
        base_command="keyword",
    )


@pytest.mark.asyncio
async def test_stash_tags_window_when_style_configured(styled_extension):
    """Stashing a window tags it when style is configured."""
    styled_extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": True,
        "workspace": {"id": 1, "name": "1"},
    }

    await styled_extension.run_stash()

    styled_extension.backend.execute.assert_called_once_with("tagwindow +stash address:0xabc")


@pytest.mark.asyncio
async def test_stash_does_not_tag_without_style(extension):
    """Stashing a window does not tag it when style is empty."""
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": True,
        "workspace": {"id": 1, "name": "1"},
    }

    await extension.run_stash()

    for call in extension.backend.execute.call_args_list:
        assert "tagwindow" not in str(call)


@pytest.mark.asyncio
async def test_unstash_untags_window_when_style_configured(styled_extension):
    """Unstashing a window from special workspace untags it."""
    styled_extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "workspace": {"id": -99, "name": "special:stash-default"},
    }

    await styled_extension.run_stash()

    styled_extension.backend.execute.assert_called_once_with("tagwindow -stash address:0xabc")


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

    styled_extension.backend.execute.assert_called_once_with("tagwindow -stash address:0xaaa")
