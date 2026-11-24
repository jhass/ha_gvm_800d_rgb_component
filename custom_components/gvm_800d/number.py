"""Number entities for GVM 800D RGB."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GvmDeviceCoordinator
from .const import (
    CMD_MODE,
    CMD_SPEED,
    DOMAIN,
    MODE_EFFECT,
    SPEED_MAX_MS,
    SPEED_MIN_MS,
)

SPEED_DESCRIPTION = NumberEntityDescription(
    key="speed",
    name="Effect speed",
    icon="mdi:speedometer",
    native_min_value=SPEED_MIN_MS,
    native_max_value=SPEED_MAX_MS,
    native_step=100,
    native_unit_of_measurement="ms",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GVM number entities."""
    coordinator: GvmDeviceCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GvmSpeedNumber(coordinator, entry)])


class GvmNumberEntity(NumberEntity):
    """Base class for a coordinator-backed number entity."""

    _attr_should_poll = False

    def __init__(
        self,
        coordinator: GvmDeviceCoordinator,
        entry: ConfigEntry,
        description: NumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.mac.replace(':', '')}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            name=entry.title or "GVM 800D RGB",
            manufacturer="GVM",
            model="800D RGB",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator updates."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    def _handle_coordinator_update(self) -> None:
        """Update HA state from coordinator state."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return whether the light is connected."""
        return self.coordinator.available


class GvmSpeedNumber(GvmNumberEntity):
    """Control the speed of scenes and dynamic effects."""

    def __init__(self, coordinator: GvmDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the speed number."""
        super().__init__(coordinator, entry, SPEED_DESCRIPTION)

    @property
    def native_value(self) -> float | None:
        """Return the speed reported by the light."""
        return self.coordinator.state.get("speed_ms")

    async def async_set_native_value(self, value: float) -> None:
        """Send a speed value to the light."""
        if value < SPEED_MIN_MS or value > SPEED_MAX_MS:
            raise ValueError(f"speed must be between {SPEED_MIN_MS} and {SPEED_MAX_MS}")
        await self.coordinator.async_request(CMD_MODE, MODE_EFFECT)
        await self.coordinator.async_request(CMD_SPEED, round(value / 100))
