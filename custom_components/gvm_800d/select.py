"""Select entities for GVM 800D RGB."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GvmDeviceCoordinator
from .const import (
    CMD_MODE,
    CMD_SCENE_SELECT,
    DOMAIN,
    MODE_EFFECT,
    MODE_LABELS,
    SCENES,
    SCENE_BY_VALUE,
)

MODE_DESCRIPTION = SelectEntityDescription(
    key="mode",
    name="Mode",
    icon="mdi:theme-light-dark",
    options=list(MODE_LABELS),
)

SCENE_DESCRIPTION = SelectEntityDescription(
    key="scene",
    name="Scene",
    icon="mdi:sparkles",
    options=list(SCENES),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GVM select entities."""
    coordinator: GvmDeviceCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [GvmModeSelect(coordinator, entry), GvmSceneSelect(coordinator, entry)]
    )


class GvmSelectEntity(SelectEntity):
    """Base class for a coordinator-backed select entity."""

    _attr_should_poll = False

    def __init__(
        self,
        coordinator: GvmDeviceCoordinator,
        entry: ConfigEntry,
        description: SelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
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


class GvmModeSelect(GvmSelectEntity):
    """Select the light's active color mode."""

    def __init__(self, coordinator: GvmDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the mode select."""
        super().__init__(coordinator, entry, MODE_DESCRIPTION)

    @property
    def current_option(self) -> str | None:
        """Return the current mode reported by the light."""
        value = self.coordinator.state.get("mode")
        for label, byte in MODE_LABELS.items():
            if value == f"{byte:02X}":
                return label
        return None

    async def async_select_option(self, option: str) -> None:
        """Set the light mode."""
        await self.coordinator.async_request(CMD_MODE, MODE_LABELS[option])


class GvmSceneSelect(GvmSelectEntity):
    """Select the active built-in scene or effect."""

    def __init__(self, coordinator: GvmDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the scene select."""
        super().__init__(coordinator, entry, SCENE_DESCRIPTION)

    @property
    def current_option(self) -> str | None:
        """Return the current scene reported by the light."""
        value = self.coordinator.state.get("scene_detail")
        return SCENE_BY_VALUE.get(value)

    async def async_select_option(self, option: str) -> None:
        """Set the light scene."""
        await self.coordinator.async_request(CMD_MODE, MODE_EFFECT)
        await self.coordinator.async_request(CMD_SCENE_SELECT, SCENES[option])
