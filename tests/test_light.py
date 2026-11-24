import colorsys
from types import SimpleNamespace

from homeassistant.components.light import ATTR_COLOR_TEMP_KELVIN, ATTR_HS_COLOR, ColorMode

from custom_components.gvm_800d.const import (
    CMD_BRIGHTNESS,
    CMD_COLOR_TEMP,
    CMD_HUE,
    CMD_MODE,
    CMD_POWER,
    CMD_SATURATION,
    MODE_CCT,
    MODE_COLOR,
)
from custom_components.gvm_800d.light import GvmLight


class FakeCoordinator:
    def __init__(self):
        self.available = True
        self.mac = "94:C9:60:B6:CC:87"
        self.handshake = {"cct_min": 3000, "cct_max": 10000}
        self.state = {"power": False}
        self.calls = []
        self.listeners = []

    def async_add_listener(self, listener):
        self.listeners.append(listener)
        return lambda: None

    async def async_request(self, cmd, value):
        self.calls.append((cmd, value))


def make_light():
    coordinator = FakeCoordinator()
    entry = SimpleNamespace(title="GVM 800D RGB")
    return GvmLight(coordinator, entry), coordinator


def test_reports_state():
    light, coordinator = make_light()
    coordinator.state = {
        "power": True,
        "brightness": 50,
        "hue": 180,
        "saturation": 80,
        "cct_kelvin": 5600,
    }
    assert light.is_on is True
    assert light.brightness == 128
    assert light.hs_color == (180, 80)
    assert light.color_temp_kelvin == 5600
    assert light.min_color_temp_kelvin == 3000
    assert light.max_color_temp_kelvin == 10000
    assert ColorMode.HS in light.supported_color_modes
    assert ColorMode.RGB in light.supported_color_modes
    assert ColorMode.COLOR_TEMP in light.supported_color_modes


async def test_turn_on_with_hs_color():
    light, coordinator = make_light()
    await light.async_turn_on(**{ATTR_HS_COLOR: (180, 80)})
    assert (CMD_POWER, 1) in coordinator.calls
    assert (CMD_MODE, MODE_COLOR) in coordinator.calls
    assert (CMD_HUE, 36) in coordinator.calls
    assert (CMD_SATURATION, 80) in coordinator.calls
    assert light.color_mode is ColorMode.HS


async def test_turn_on_with_color_temp():
    light, coordinator = make_light()
    await light.async_turn_on(**{ATTR_COLOR_TEMP_KELVIN: 12000})
    assert (CMD_MODE, MODE_CCT) in coordinator.calls
    assert (CMD_COLOR_TEMP, 100) in coordinator.calls
    assert light.color_mode is ColorMode.COLOR_TEMP


async def test_turn_on_with_brightness_and_turn_off():
    light, coordinator = make_light()
    await light.async_turn_on(brightness=255)
    assert (CMD_BRIGHTNESS, 100) in coordinator.calls
    await light.async_turn_off()
    assert (CMD_POWER, 0) in coordinator.calls


def test_rgb_color_round_trip():
    light, coordinator = make_light()
    coordinator.state = {"power": True, "hue": 120, "saturation": 100}
    red, green, blue = light.rgb_color
    hue, saturation, _value = colorsys.rgb_to_hsv(
        red / 255, green / 255, blue / 255
    )
    assert round(hue * 360 / 5) * 5 == 120
    assert round(saturation * 100) == 100
