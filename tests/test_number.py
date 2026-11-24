from types import SimpleNamespace

import pytest

from custom_components.gvm_800d.const import (
    CMD_MODE,
    CMD_SPEED,
    SPEED_MAX_MS,
    SPEED_MIN_MS,
)
from custom_components.gvm_800d.number import GvmSpeedNumber


class FakeCoordinator:
    def __init__(self, state=None):
        self.mac = "94:C9:60:B6:CC:87"
        self.available = True
        self.state = state if state is not None else {}
        self.requests = []

    def async_add_listener(self, listener):
        self.listener = listener
        return lambda: None

    async def async_request(self, cmd, value):
        self.requests.append((cmd, value))


def make_number(state=None):
    coordinator = FakeCoordinator(state)
    entry = SimpleNamespace(title="BT_LED")
    return coordinator, GvmSpeedNumber(coordinator, entry)


def test_speed_number_reports_device_state():
    _coordinator, number = make_number({"speed_ms": 2900})
    assert number.native_min_value == SPEED_MIN_MS
    assert number.native_max_value == SPEED_MAX_MS
    assert number.native_step == 100
    assert number.native_value == 2900
    assert number.native_unit_of_measurement == "ms"


async def test_speed_number_sends_command():
    coordinator, number = make_number()
    await number.async_set_native_value(1200)
    assert coordinator.requests == [(CMD_MODE, 3), (CMD_SPEED, 12)]


async def test_speed_number_rejects_out_of_range():
    _coordinator, number = make_number()
    with pytest.raises(ValueError):
        await number.async_set_native_value(99)
