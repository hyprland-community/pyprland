import pytest

from pyprland.plugins.stash import Extension
from tests.conftest import make_extension


CONFIG = {
    "S": {
        "animation": "",
        "size": "24% 54%",
        "position": "76% 22%",
        "preserve_aspect": False,
    },
    "C": {
        "animation": "",
        "size": "24% 54%",
        "position": "76% 22%",
        "preserve_aspect": True,
    },
}

MONITOR = {
    "x": 10,
    "y": 20,
    "width": 1000,
    "height": 800,
    "scale": 1.0,
    "transform": 0,
}


@pytest.fixture
def extension():
    ext = make_extension(Extension, config=CONFIG)
    ext.backend.get_monitor_props.return_value = MONITOR
    ext.backend.get_client_props.return_value = {"size": [600, 400], "at": [770, 196]}
    return ext


@pytest.mark.asyncio
async def test_stash_send_moves_window_to_named_special_workspace(extension):
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": False,
        "workspace": {"id": 1, "name": "1"},
    }

    await extension.run_stash_send("S")

    extension.backend.move_window_to_workspace.assert_called_once_with("0xabc", "special:st-S", silent=True)
    extension.backend.toggle_floating.assert_called_once_with("0xabc")
    assert extension._slots["S"].address == "0xabc"
    assert extension._slots["S"].visible is False
    assert extension._addr_to_stash == {"0xabc": "S"}


@pytest.mark.asyncio
async def test_stash_send_keeps_already_floating_window_floating(extension):
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": True,
        "workspace": {"id": 1, "name": "1"},
    }

    await extension.run_stash_send("S")

    extension.backend.move_window_to_workspace.assert_called_once_with("0xabc", "special:st-S", silent=True)
    extension.backend.toggle_floating.assert_not_called()
    assert extension._slots["S"].was_floating is True


@pytest.mark.asyncio
async def test_stash_send_on_focused_visible_stash_releases_to_active_workspace(extension):
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": False,
        "workspace": {"id": 1, "name": "1"},
    }
    await extension.run_stash_send("S")
    await extension.run_stash_toggle("S")

    extension.backend.reset_mock()
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": True,
        "workspace": {"id": 1, "name": "1"},
    }

    await extension.run_stash_send("S")

    extension.backend.pin_window.assert_called_once_with("0xabc")
    extension.backend.move_window_to_workspace.assert_called_once_with("0xabc", "1", silent=True)
    extension.backend.toggle_floating.assert_called_once_with("0xabc")
    extension.backend.focus_window.assert_called_once_with("0xabc")
    assert extension._slots["S"].address == ""
    assert extension._slots["S"].visible is False
    assert extension._addr_to_stash == {}


@pytest.mark.asyncio
async def test_stash_toggle_show_moves_window_to_active_workspace_and_pins_it(extension):
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": False,
        "workspace": {"id": 1, "name": "1"},
    }
    await extension.run_stash_send("S")

    extension.backend.reset_mock()

    await extension.run_stash_toggle("S")

    extension.backend.move_window_to_workspace.assert_called_once_with("0xabc", "1", silent=True)
    extension.backend.resize_window.assert_called_once_with("0xabc", 240, 432)
    extension.backend.move_window.assert_called_once_with("0xabc", 770, 196)
    extension.backend.pin_window.assert_called_once_with("0xabc")
    extension.backend.focus_window.assert_called_once_with("0xabc")
    assert extension._slots["S"].visible is True


@pytest.mark.asyncio
async def test_stash_toggle_hide_unpins_and_returns_window_to_hidden_workspace(extension):
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": False,
        "workspace": {"id": 1, "name": "1"},
    }
    await extension.run_stash_send("S")
    await extension.run_stash_toggle("S")

    extension.backend.reset_mock()

    await extension.run_stash_toggle("S")

    extension.backend.pin_window.assert_called_once_with("0xabc")
    extension.backend.move_window_to_workspace.assert_called_once_with("0xabc", "special:st-S", silent=True)
    assert extension._slots["S"].visible is False


@pytest.mark.asyncio
async def test_stash_toggle_restores_saved_geometry_when_configured(extension):
    extension.backend.execute_json.return_value = {
        "address": "0xdef",
        "floating": True,
        "workspace": {"id": 1, "name": "1"},
    }
    await extension.run_stash_send("C")

    await extension.run_stash_toggle("C")

    extension.backend.reset_mock()
    extension.backend.get_client_props.return_value = {"size": [333, 222], "at": [500, 250]}

    await extension.run_stash_toggle("C")

    extension.backend.reset_mock()

    await extension.run_stash_toggle("C")

    extension.backend.resize_window.assert_called_once_with("0xdef", 333, 222)
    extension.backend.move_window.assert_called_once_with("0xdef", 500, 250)


@pytest.mark.asyncio
async def test_stash_toggle_restores_saved_geometry_across_scaled_monitor_origins(extension):
    scaled_monitor = {**MONITOR, "x": 1920, "y": 0, "scale": 2.0}
    target_monitor = {**MONITOR, "x": 0, "y": 0, "scale": 1.0}
    extension.backend.get_monitor_props.return_value = scaled_monitor
    extension.backend.execute_json.return_value = {
        "address": "0xdef",
        "floating": True,
        "workspace": {"id": 1, "name": "1"},
    }
    await extension.run_stash_send("C")
    await extension.run_stash_toggle("C")

    extension.backend.reset_mock()
    extension.backend.get_client_props.return_value = {"size": [333, 222], "at": [2100, 120]}

    await extension.run_stash_toggle("C")

    extension.backend.reset_mock()
    extension.backend.get_monitor_props.return_value = target_monitor

    await extension.run_stash_toggle("C")

    extension.backend.resize_window.assert_called_once_with("0xdef", 333, 222)
    extension.backend.move_window.assert_called_once_with("0xdef", 180, 120)


@pytest.mark.asyncio
async def test_stash_send_replaces_existing_window_in_same_stash(extension):
    extension.backend.execute_json.return_value = {
        "address": "0xold",
        "floating": False,
        "workspace": {"id": 1, "name": "1"},
    }
    await extension.run_stash_send("S")

    extension.backend.reset_mock()
    extension.backend.execute_json.return_value = {
        "address": "0xnew",
        "floating": False,
        "workspace": {"id": 2, "name": "2"},
    }

    await extension.run_stash_send("S")

    calls = extension.backend.move_window_to_workspace.call_args_list
    assert calls[0].args == ("0xold", "1")
    assert calls[0].kwargs == {"silent": True}
    assert calls[1].args == ("0xnew", "special:st-S")
    assert calls[1].kwargs == {"silent": True}
    extension.backend.focus_window.assert_not_called()
    assert extension.backend.toggle_floating.call_args_list[0].args == ("0xold",)
    assert extension.backend.toggle_floating.call_args_list[1].args == ("0xnew",)
    assert extension._slots["S"].address == "0xnew"
    assert extension._addr_to_stash == {"0xnew": "S"}


@pytest.mark.asyncio
async def test_stash_send_preserves_original_floating_state_when_moving_between_stashes(extension):
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": False,
        "workspace": {"id": 1, "name": "1"},
    }
    await extension.run_stash_send("S")
    await extension.run_stash_toggle("S")

    extension.backend.reset_mock()
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": True,
        "workspace": {"id": 1, "name": "1"},
    }

    await extension.run_stash_send("C")

    extension.backend.toggle_floating.assert_not_called()
    assert extension._slots["C"].was_floating is False

    await extension.run_stash_toggle("C")

    extension.backend.reset_mock()
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": True,
        "workspace": {"id": 1, "name": "1"},
    }

    await extension.run_stash_send("C")

    extension.backend.toggle_floating.assert_called_once_with("0xabc")


@pytest.mark.asyncio
async def test_closewindow_clears_stash_tracking(extension):
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": False,
        "workspace": {"id": 1, "name": "1"},
    }
    await extension.run_stash_send("S")

    await extension.event_closewindow("abc")

    assert extension._slots["S"].address == ""
    assert extension._slots["S"].visible is False
    assert extension._addr_to_stash == {}


@pytest.mark.asyncio
async def test_exit_releases_hidden_stash_to_active_workspace(extension):
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": False,
        "workspace": {"id": 1, "name": "1"},
    }
    await extension.run_stash_send("S")

    extension.backend.reset_mock()

    await extension.exit()

    extension.backend.pin_window.assert_not_called()
    extension.backend.move_window_to_workspace.assert_called_once_with("0xabc", "1", silent=True)
    extension.backend.toggle_floating.assert_called_once_with("0xabc")
    extension.backend.focus_window.assert_not_called()
    assert extension._slots["S"].address == ""


@pytest.mark.asyncio
async def test_on_reload_releases_removed_occupied_stash(extension):
    extension.backend.execute_json.return_value = {
        "address": "0xabc",
        "floating": False,
        "workspace": {"id": 1, "name": "1"},
    }
    await extension.run_stash_send("S")

    extension.backend.reset_mock()
    extension.config.clear()
    extension.config.update({"C": CONFIG["C"]})

    await extension.on_reload()

    extension.backend.move_window_to_workspace.assert_called_once_with("0xabc", "1", silent=True)
    extension.backend.toggle_floating.assert_called_once_with("0xabc")
    extension.backend.focus_window.assert_not_called()
    assert "S" not in extension._slots
    assert extension._addr_to_stash == {}


def test_validate_config_static_accepts_named_stash_sections():
    errors = Extension.validate_config_static("stash", CONFIG)

    assert errors == []


def test_validate_config_static_rejects_non_table_sections():
    errors = Extension.validate_config_static("stash", {"S": "bad"})

    assert errors == ["[stash] section 'S' must be a table"]
