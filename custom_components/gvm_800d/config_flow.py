"""Config flow for GVM 800D RGB."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_MAC, DOMAIN

if TYPE_CHECKING:
    from homeassistant.components.bluetooth import BluetoothServiceInfoBleak


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
        self._name: str = "BT_LED"

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual MAC entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                mac = normalize_mac(user_input[CONF_MAC])
            except ValueError:
                errors[CONF_MAC] = "invalid_mac"
            else:
                await self.async_set_unique_id(mac.replace(":", ""))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"GVM 800D RGB ({mac})", data={CONF_MAC: mac}
                )
        return self.async_show_form(
            step_id="user",
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
        self._name = discovery_info.name or "BT_LED"
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
