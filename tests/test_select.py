from types import SimpleNamespace

from custom_components.gvm_800d.const import (
    CMD_MODE,
    MODE_CCT_LABEL,
    MODE_COLOR_LABEL,
)
from custom_components.gvm_800d.select import GvmModeSelect


class FakeCoordinator:
    def __init__(self):
        self.mac = "94:C9:60:B6:CC:87"
        self.available = True
        self.state = {"mode": "01"}
        self.handshake = None
        self.requests = []

    def async_add_listener(self, listener):
        self.listener = listener
        return lambda: None

    async def async_request(self, cmd, value):
        self.requests.append((cmd, value))


def make_select():
    coordinator = FakeCoordinator()
    entry = SimpleNamespace(title="BT_LED")
    return coordinator, GvmModeSelect(coordinator, entry)


def test_mode_select_reports_device_state():
    coordinator, select = make_select()
    assert select.options == [MODE_CCT_LABEL, MODE_COLOR_LABEL]
    assert select.current_option == MODE_CCT_LABEL
    assert select.available is True

    coordinator.state = {"mode": "02"}
    select.async_write_ha_state = lambda: None
    select._handle_coordinator_update()
    assert select.current_option == MODE_COLOR_LABEL


async def test_mode_select_sends_command():
    _coordinator, select = make_select()
    await select.async_select_option(MODE_COLOR_LABEL)
    assert select.coordinator.requests == [(CMD_MODE, 2)]
