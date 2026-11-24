from types import SimpleNamespace

import pytest
from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_USER
from homeassistant.const import CONF_MAC
from homeassistant.data_entry_flow import FlowResultType

from custom_components.gvm_800d import config_flow as config_flow_module
from custom_components.gvm_800d.config_flow import normalize_mac
from custom_components.gvm_800d.const import ACTION_MANUAL, ACTION_RESCAN, CONF_DEVICE, DOMAIN

MAC = "94:C9:60:B6:CC:87"


def discovery_info(address=MAC, name="BT_LED", service_uuids=None):
    """Return a minimal discovered advertisement."""
    return SimpleNamespace(
        address=address,
        name=name,
        service_uuids=service_uuids or [],
    )


def device_options(result):
    """Return the selectable device map from a config flow form."""
    schema = result["data_schema"].schema
    key = next(key for key in schema if str(key.schema) == CONF_DEVICE)
    return schema[key].container


def test_normalize_mac():
    assert normalize_mac("94:c9:60:b6:cc:87") == MAC
    with pytest.raises(ValueError):
        normalize_mac("not-a-mac")


async def test_user_flow_lists_discovered_lights(hass, monkeypatch):
    monkeypatch.setattr(
        config_flow_module.bluetooth,
        "async_discovered_service_info",
        lambda hass, connectable=True: [
            discovery_info(),
            discovery_info("11:22:33:44:55:66", "Unrelated"),
        ],
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    options = device_options(result)
    assert options[MAC] == f"BT_LED ({MAC})"
    assert ACTION_MANUAL in options
    assert ACTION_RESCAN in options
    assert "11:22:33:44:55:66" not in options

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_DEVICE: MAC}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_MAC: MAC}
    entries = hass.config_entries.async_entries(DOMAIN)
    assert entries[0].unique_id == "94C960B6CC87"


async def test_user_flow_falls_back_to_manual_mac(hass, monkeypatch):
    monkeypatch.setattr(
        config_flow_module.bluetooth,
        "async_discovered_service_info",
        lambda hass, connectable=True: [],
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert device_options(result) == {
        ACTION_MANUAL: "Enter MAC address manually",
        ACTION_RESCAN: "Rescan for lights",
    }

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_DEVICE: ACTION_MANUAL}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MAC: "94:c9:60:b6:cc:87"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_MAC: MAC}


async def test_user_flow_rescan(hass, monkeypatch):
    monkeypatch.setattr(
        config_flow_module.bluetooth,
        "async_discovered_service_info",
        lambda hass, connectable=True: [],
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    monkeypatch.setattr(
        config_flow_module.bluetooth,
        "async_discovered_service_info",
        lambda hass, connectable=True: [discovery_info()],
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_DEVICE: ACTION_RESCAN}
    )
    assert result["type"] is FlowResultType.FORM
    assert MAC in device_options(result)


async def test_bluetooth_discovery_creates_entry(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_BLUETOOTH},
        data=discovery_info(),
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_MAC: MAC}
