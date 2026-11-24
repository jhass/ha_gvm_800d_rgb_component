"""Light platform for GVM 800D RGB."""

from __future__ import annotations

import colorsys
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GvmDeviceCoordinator
from .const import (
    CMD_BRIGHTNESS,
    CMD_COLOR_TEMP,
    CMD_HUE,
    CMD_MODE,
    CMD_POWER,
    CMD_SATURATION,
    DOMAIN,
    MODE_CCT,
    MODE_COLOR,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the GVM light entity."""
    coordinator: GvmDeviceCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GvmLight(coordinator, entry)])


class GvmLight(LightEntity):
    """Represent one GVM 800D RGB light."""

    _attr_should_poll = False
    _attr_supported_color_modes = {
        ColorMode.HS,
        ColorMode.RGB,
        ColorMode.COLOR_TEMP,
    }

    def __init__(self, coordinator: GvmDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the light entity."""
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{coordinator.mac.replace(':', '')}_light"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            name=entry.title or "GVM 800D RGB",
            manufacturer="GVM",
            model="800D RGB",
        )
        self._active_mode = ColorMode.HS

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator updates."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    def _handle_coordinator_update(self) -> None:
        """Update HA state from coordinator state."""
        mode = self.coordinator.state.get("mode")
        if mode == "01":
            self._active_mode = ColorMode.COLOR_TEMP
        elif mode == "02":
            self._active_mode = ColorMode.HS
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return whether the light is connected."""
        return self.coordinator.available

    @property
    def is_on(self) -> bool:
        """Return whether the light is on."""
        return bool(self.coordinator.state.get("power", False))

    @property
    def brightness(self) -> int | None:
        """Return brightness in the Home Assistant 0-255 range."""
        brightness = self.coordinator.state.get("brightness")
        if brightness is None:
            return None
        return round(brightness * 255 / 100)

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return hue and saturation."""
        hue = self.coordinator.state.get("hue")
        saturation = self.coordinator.state.get("saturation")
        if hue is None or saturation is None:
            return None
        return float(hue), float(saturation)

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return RGB derived from the native HS state."""
        if self.hs_color is None:
            return None
        hue, saturation = self.hs_color
        red, green, blue = colorsys.hsv_to_rgb(hue / 360, saturation / 100, 1.0)
        return round(red * 255), round(green * 255), round(blue * 255)

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return color temperature in Kelvin."""
        return self.coordinator.state.get("cct_kelvin")

    @property
    def min_color_temp_kelvin(self) -> int:
        """Return the minimum supported color temperature."""
        if self.coordinator.handshake is None:
            return 2000
        return self.coordinator.handshake["cct_min"]

    @property
    def max_color_temp_kelvin(self) -> int:
        """Return the maximum supported color temperature."""
        if self.coordinator.handshake is None:
            return 6500
        return self.coordinator.handshake["cct_max"]

    @property
    def color_mode(self) -> ColorMode:
        """Return the active color mode."""
        return self._active_mode

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light or apply requested attributes."""
        if not self.is_on:
            await self.coordinator.async_request(CMD_POWER, 1)

        brightness = kwargs.get(ATTR_BRIGHTNESS)
        if brightness is not None:
            await self.coordinator.async_request(
                CMD_BRIGHTNESS, round(brightness * 100 / 255)
            )

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            value = self._kelvin_to_device(kwargs[ATTR_COLOR_TEMP_KELVIN])
            await self.coordinator.async_request(CMD_MODE, MODE_CCT)
            await self.coordinator.async_request(CMD_COLOR_TEMP, value)
            self._active_mode = ColorMode.COLOR_TEMP
        elif ATTR_HS_COLOR in kwargs:
            hue, saturation = kwargs[ATTR_HS_COLOR]
            hue_byte, saturation_byte = self._hs_to_device(hue, saturation)
            await self.coordinator.async_request(CMD_MODE, MODE_COLOR)
            await self.coordinator.async_request(CMD_HUE, hue_byte)
            await self.coordinator.async_request(CMD_SATURATION, saturation_byte)
            self._active_mode = ColorMode.HS
        elif ATTR_RGB_COLOR in kwargs:
            hue, saturation = self._rgb_to_hs(kwargs[ATTR_RGB_COLOR])
            hue_byte, saturation_byte = self._hs_to_device(hue, saturation)
            await self.coordinator.async_request(CMD_MODE, MODE_COLOR)
            await self.coordinator.async_request(CMD_HUE, hue_byte)
            await self.coordinator.async_request(CMD_SATURATION, saturation_byte)
            self._active_mode = ColorMode.RGB

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self.coordinator.async_request(CMD_POWER, 0)

    @staticmethod
    def _hs_to_device(hue: float, saturation: float) -> tuple[int, int]:
        """Convert HA HS values to device bytes."""
        hue_byte = round((hue % 360) / 5) % 76
        saturation_byte = max(0, min(100, round(saturation)))
        return hue_byte, saturation_byte

    @staticmethod
    def _rgb_to_hs(rgb: tuple[int, int, int]) -> tuple[float, float]:
        """Convert RGB to HS."""
        red, green, blue = (channel / 255 for channel in rgb)
        hue, saturation, _value = colorsys.rgb_to_hsv(red, green, blue)
        return hue * 360, saturation * 100

    def _kelvin_to_device(self, kelvin: int) -> int:
        """Convert Kelvin to the device's Kelvin/100 byte."""
        clamped = max(
            self.min_color_temp_kelvin, min(self.max_color_temp_kelvin, kelvin)
        )
        return round(clamped / 100)
