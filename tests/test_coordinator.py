import asyncio
from types import SimpleNamespace

import custom_components.gvm_800d as gvm_integration
from custom_components.gvm_800d import GvmDeviceCoordinator
from custom_components.gvm_800d.const import CMD_BRIGHTNESS, CMD_POWER


class FakeClient:
    def __init__(self):
        self.connected = False
        self.commands = []
        self.on_handshake = None
        self.on_state = None

    async def async_connect(self):
        self.connected = True
        self.on_handshake(
            {
                "device_id": "00",
                "device_type": "31",
                "cct_min": 3000,
                "cct_max": 10000,
            }
        )
        self.on_state({"power": True, "brightness": 50})

    async def async_disconnect(self):
        self.connected = False

    async def send_command(self, cmd, value):
        self.commands.append((cmd, value))


def make_coordinator():
    client = FakeClient()
    entry = SimpleNamespace(entry_id="test", data={"mac": "94:C9:60:B6:CC:87"})
    coordinator = GvmDeviceCoordinator(None, entry, client=client)
    coordinator.client = client
    client.on_handshake = coordinator._on_handshake
    client.on_state = coordinator._on_state
    return coordinator, client


async def test_connect_reads_handshake_and_state():
    coordinator, client = make_coordinator()
    await coordinator.async_connect()
    assert coordinator.available is True
    assert coordinator.handshake["device_type"] == "31"
    assert coordinator.state["brightness"] == 50
    assert client.connected is True


async def test_request_coalesces_same_command():
    coordinator, client = make_coordinator()
    await coordinator.async_connect()
    await asyncio.gather(
        coordinator.async_request(CMD_BRIGHTNESS, 10),
        coordinator.async_request(CMD_BRIGHTNESS, 20),
        coordinator.async_request(CMD_POWER, 1),
    )
    assert (CMD_POWER, 1) in client.commands
    assert (CMD_BRIGHTNESS, 20) in client.commands
    assert (CMD_BRIGHTNESS, 10) not in client.commands


def test_default_client_receives_hass_and_name(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, mac, hass=None, name=None, **kwargs):
            captured["mac"] = mac
            captured["hass"] = hass
            captured["name"] = name

    monkeypatch.setattr(gvm_integration, "GvmBleClient", FakeClient)
    hass = SimpleNamespace()
    entry = SimpleNamespace(
        entry_id="test",
        data={"mac": "94:C9:60:B6:CC:87"},
        title="BT_LED",
    )

    gvm_integration.GvmDeviceCoordinator(hass, entry)

    assert captured == {
        "mac": "94:C9:60:B6:CC:87",
        "hass": hass,
        "name": "BT_LED",
    }
