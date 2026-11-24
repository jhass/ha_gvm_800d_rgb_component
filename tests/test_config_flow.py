import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_MAC
from homeassistant.data_entry_flow import FlowResultType

from custom_components.gvm_800d.config_flow import normalize_mac
from custom_components.gvm_800d.const import DOMAIN


def test_normalize_mac():
    assert normalize_mac("94:c9:60:b6:cc:87") == "94:C9:60:B6:CC:87"
    with pytest.raises(ValueError):
        normalize_mac("not-a-mac")


async def test_user_flow_creates_entry(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MAC: "94:c9:60:b6:cc:87"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_MAC: "94:C9:60:B6:CC:87"}
    entries = hass.config_entries.async_entries(DOMAIN)
    assert entries[0].unique_id == "94C960B6CC87"
