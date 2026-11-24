"""Config flow for GVM 800D RGB."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import (
    ACTION_MANUAL,
    ACTION_RESCAN,
    CONF_DEVICE,
    CONF_MAC,
    DOMAIN,
    SERVICE_UUID,
)

if TYPE_CHECKING:
    from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

DEVICE_NAME = "BT_LED"


def normalize_mac(value: str) -> str:
    """Normalize a MAC address to uppercase colon-separated form."""
    compact = re.sub(r"[^0-9A-Fa-f]", "", value)
    if len(compact) != 12:
        raise ValueError("invalid MAC address")
    return ":".join(compact[index : index + 2].upper() for index in range(0, 12, 2))


def normalize_address(value: str) -> str:
    """Normalize a BLE MAC address or macOS-style UUID."""
    compact = re.sub(r"[^0-9A-Fa-f]", "", value).upper()
    if len(compact) == 12:
        return normalize_mac(compact)
    if len(compact) == 32:
        groups = (8, 4, 4, 4, 12)
        parts = []
        position = 0
        for size in groups:
            parts.append(compact[position : position + size])
            position += size
        return "-".join(parts)
    raise ValueError("invalid Bluetooth address")


def _unique_id(address: str) -> str:
    """Return a config entry unique ID for a MAC or UUID address."""
    return re.sub(r"[^0-9A-Fa-f]", "", address).upper()


class Gvm800dConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle discovery and manual setup of GVM 800D RGB lights."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow state."""
        self._address: str | None = None
        self._name: str = DEVICE_NAME

    def _discovered_devices(self) -> dict[str, str]:
        """Return discovered GVM lights keyed by normalized BLE address."""
        devices: dict[str, str] = {}
        for info in bluetooth.async_discovered_service_info(self.hass, connectable=False):
            name = (getattr(info, "name", None) or DEVICE_NAME).strip()
            services = {
                str(uuid).lower()
                for uuid in (getattr(info, "service_uuids", None) or [])
            }
            is_gvm = DEVICE_NAME in name.upper() or SERVICE_UUID.lower() in services
            if not is_gvm:
                continue
            try:
                address = normalize_address(info.address)
            except ValueError:
                continue
            devices[address] = f"{name} ({address})"
        return devices

    async def _async_create_entry(self, address: str, name: str) -> ConfigFlowResult:
        """Create an entry for a discovered or manually entered light."""
        await self.async_set_unique_id(_unique_id(address))
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=f"{name} ({address})", data={CONF_MAC: address}
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show a scanner-driven list of nearby lights."""
        if user_input is not None:
            selection = user_input[CONF_DEVICE]
            if selection == ACTION_RESCAN:
                return await self.async_step_user()
            if selection == ACTION_MANUAL:
                return await self.async_step_manual()
            devices = self._discovered_devices()
            return await self._async_create_entry(
                selection, devices.get(selection, "GVM 800D RGB")
            )

        devices = self._discovered_devices()
        options: dict[str, str] = {
            address: label for address, label in devices.items()
        }
        options[ACTION_MANUAL] = "Enter MAC address manually"
        options[ACTION_RESCAN] = "Rescan for lights"
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_DEVICE): vol.In(options)}
            ),
            description_placeholders={"count": str(len(devices))},
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual MAC entry as a fallback."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                address = normalize_address(user_input[CONF_MAC])
            except ValueError:
                errors[CONF_MAC] = "invalid_mac"
            else:
                return await self._async_create_entry(address, "GVM 800D RGB")
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required(CONF_MAC): str}),
            errors=errors,
        )

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a discovered BT_LED advertisement."""
        address = normalize_address(discovery_info.address)
        await self.async_set_unique_id(_unique_id(address))
        self._abort_if_unique_id_configured()
        self._address = address
        self._name = discovery_info.name or DEVICE_NAME
        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered light."""
        if user_input is not None and self._address is not None:
            return self.async_create_entry(
                title=f"{self._name} ({self._address})",
                data={CONF_MAC: self._address},
            )
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self._name,
                "mac": self._address or "",
            },
        )
