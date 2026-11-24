from types import SimpleNamespace

import pytest

from custom_components.gvm_800d.const import (
    CMD_MODE,
    CMD_SCENE_SELECT,
    MODE_CCT_LABEL,
    MODE_COLOR_LABEL,
    MODE_EFFECT_LABEL,
    SCENES,
)
from custom_components.gvm_800d.select import (
    GvmModeSelect,
    GvmSceneSelect,
)


class FakeCoordinator:
    def __init__(self, state=None):
        self.mac = "94:C9:60:B6:CC:87"
        self.available = True
        self.state = state if state is not None else {"mode": "01"}
        self.handshake = None
        self.requests = []

    def async_add_listener(self, listener):
        self.listener = listener
        return lambda: None

    async def async_request(self, cmd, value):
        self.requests.append((cmd, value))


def make_select(select_class, state=None):
    coordinator = FakeCoordinator(state)
    entry = SimpleNamespace(title="BT_LED")
    return coordinator, select_class(coordinator, entry)


def test_mode_select_reports_device_state():
    coordinator, select = make_select(GvmModeSelect)
    assert select.options == [
        MODE_CCT_LABEL,
        MODE_COLOR_LABEL,
        MODE_EFFECT_LABEL,
    ]
    assert select.current_option == MODE_CCT_LABEL
    assert select.available is True

    coordinator.state = {"mode": "02"}
    select.async_write_ha_state = lambda: None
    select._handle_coordinator_update()
    assert select.current_option == MODE_COLOR_LABEL


async def test_mode_select_sends_command():
    _coordinator, select = make_select(GvmModeSelect)
    await select.async_select_option(MODE_EFFECT_LABEL)
    assert select.coordinator.requests == [(CMD_MODE, 3)]


def test_scene_select_lists_rgb31_scenes_and_reports_state():
    _coordinator, select = make_select(GvmSceneSelect, {"scene_detail": 13})
    assert select.options == list(SCENES)
    assert select.current_option == "Welding"


async def test_scene_select_sends_command():
    _coordinator, select = make_select(GvmSceneSelect)
    await select.async_select_option("SOS")
    assert select.coordinator.requests == [(CMD_MODE, 3), (CMD_SCENE_SELECT, 18)]
