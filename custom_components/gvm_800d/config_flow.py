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


class Gvm800dConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle discovery and manual setup of GVM 800D RGB lights."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow state."""
        self._mac: str | None = None
        self._name: str = DEVICE_NAME

    def _discovered_devices(self) -> dict[str, str]:
        """Return discovered GVM lights keyed by normalized MAC address."""
        devices: dict[str, str] = {}
        for info in bluetooth.async_discovered_service_info(self.hass, connectable=True):
            name = (getattr(info, "name", None) or DEVICE_NAME).strip()
            services = {
                str(uuid).lower()
                for uuid in (getattr(info, "service_uuids", None) or [])
            }
            is_gvm = name.upper() == DEVICE_NAME or SERVICE_UUID.lower() in services
            if not is_gvm:
                continue
            try:
                mac = normalize_mac(info.address)
            except ValueError:
                continue
            devices[mac] = f"{name} ({mac})"
        return devices

    async def _async_create_entry(self, mac: str, name: str) -> ConfigFlowResult:
        """Create an entry for a discovered or manually entered light."""
        await self.async_set_unique_id(mac.replace(":", ""))
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=f"{name} ({mac})", data={CONF_MAC: mac})

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
                mac = normalize_mac(user_input[CONF_MAC])
            except ValueError:
                errors[CONF_MAC] = "invalid_mac"
            else:
                return await self._async_create_entry(mac, "GVM 800D RGB")
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required(CONF_MAC): str}),
            errors=errors,
        )

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a discovered BT_LED advertisement."""
        mac = normalize_mac(discovery_info.address)
        await self.async_set_unique_id(mac.replace(":", ""))
        self._abort_if_unique_id_configured()
        self._mac = mac
        self._name = discovery_info.name or DEVICE_NAME
        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered light."""
        if user_input is not None and self._mac is not None:
            return self.async_create_entry(
                title=f"{self._name} ({self._mac})", data={CONF_MAC: self._mac}
            )
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._name, "mac": self._mac or ""},
        )
