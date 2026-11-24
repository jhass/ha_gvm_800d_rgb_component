from types import SimpleNamespace

import pytest
from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_USER
from homeassistant.const import CONF_MAC
from homeassistant.data_entry_flow import FlowResultType

from custom_components.gvm_800d import config_flow as config_flow_module
from custom_components.gvm_800d.config_flow import normalize_address, normalize_mac
from custom_components.gvm_800d.const import ACTION_MANUAL, ACTION_RESCAN, CONF_DEVICE, DOMAIN

MAC = "94:C9:60:B6:CC:87"
SECOND_MAC = "94:C9:60:B6:C6:BB"
BLE_UUID = "FB59B4A5-2E3C-66E2-DF68-3128E5DEC6BD"


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


def test_normalize_address_accepts_macs_and_ble_uuids():
    assert normalize_address("94:c9:60:b6:c6:bb") == SECOND_MAC
    assert normalize_address("fb59b4a5-2e3c-66e2-df68-3128e5dec6bd") == BLE_UUID
    with pytest.raises(ValueError):
        normalize_address("not-an-address")


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


async def test_user_flow_lists_multiple_lights_from_all_history(hass, monkeypatch):
    calls = []

    def discovered(_hass, connectable=True):
        calls.append(connectable)
        if connectable:
            return [discovery_info()]
        return [
            discovery_info(),
            discovery_info(SECOND_MAC),
            discovery_info(BLE_UUID, "BT_LED_2"),
        ]

    monkeypatch.setattr(
        config_flow_module.bluetooth, "async_discovered_service_info", discovered
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    options = device_options(result)
    assert options[SECOND_MAC] == f"BT_LED ({SECOND_MAC})"
    assert options[BLE_UUID] == f"BT_LED_2 ({BLE_UUID})"
    assert False in calls


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


async def test_bluetooth_discovery_accepts_ble_uuid(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_BLUETOOTH},
        data=discovery_info(BLE_UUID),
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_MAC: BLE_UUID}
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.unique_id == BLE_UUID.replace("-", "")


async def test_manual_flow_accepts_ble_uuid(hass, monkeypatch):
    monkeypatch.setattr(
        config_flow_module.bluetooth,
        "async_discovered_service_info",
        lambda hass, connectable=True: [],
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_DEVICE: ACTION_MANUAL}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MAC: BLE_UUID.lower()}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_MAC: BLE_UUID}
