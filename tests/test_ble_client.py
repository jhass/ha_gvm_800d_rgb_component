import asyncio
from types import SimpleNamespace

from bleak_retry_connector import BleakClientWithServiceCache

import custom_components.gvm_800d.ble as ble_module
from custom_components.gvm_800d.ble import GvmBleClient
from custom_components.gvm_800d.const import CHARACTERISTIC_UUID


class FakeBleakClient:
    def __init__(self, address):
        self.address = address
        self.connected = False
        self.writes = []
        self.notify_callback = None
        self.connect_calls = 0

    async def connect(self):
        self.connect_calls += 1
        self.connected = True

    async def disconnect(self):
        self.connected = False

    async def start_notify(self, uuid, callback):
        assert uuid == CHARACTERISTIC_UUID
        self.notify_callback = callback

    async def write_gatt_char(self, uuid, data, response=False):
        assert uuid == CHARACTERISTIC_UUID
        assert response is True
        self.writes.append(data.decode("ascii"))


def make_client():
    holder = {}

    async def factory():
        holder["client"] = FakeBleakClient("94:C9:60:B6:CC:87")
        holder["client"].connected = True
        return holder["client"]

    return holder, factory


async def test_connect_sends_handshake():
    holder, factory = make_client()
    client = GvmBleClient("94:C9:60:B6:CC:87", connect_factory=factory)
    await client.async_connect()
    assert holder["client"].connected is True
    assert holder["client"].writes == ["4C5409000053000001009474\r\n"]


async def test_send_command_writes_captured_frame():
    holder, factory = make_client()
    client = GvmBleClient("94:C9:60:B6:CC:87", connect_factory=factory)
    await client.async_connect()
    holder["client"].writes.clear()
    await client.send_command(0x06, 0x01)
    assert holder["client"].writes == ["4C540900315700060101D5DF\r\n"]


async def test_notification_updates_state_and_acknowledges():
    holder, factory = make_client()
    states = []
    client = GvmBleClient(
        "94:C9:60:B6:CC:87",
        on_state=states.append,
        connect_factory=factory,
    )
    await client.async_connect()
    holder["client"].notify_callback(
        None, bytearray.fromhex("4C54090031530000001E6400020B")
    )
    holder["client"].writes.clear()
    holder["client"].notify_callback(
        None, bytearray.fromhex("4C5409003103010205201B18")
    )
    await asyncio.sleep(0)
    assert states[0]["power"] is True
    assert states[0]["brightness"] == 5
    assert holder["client"].writes == ["4C540900314801020520E68F\r\n"]


async def test_connect_uses_ha_retry_connector(monkeypatch):
    device = SimpleNamespace(address="94:C9:60:B6:CC:87", name="BT_LED")
    fake_client = FakeBleakClient("94:C9:60:B6:CC:87")
    fake_client.connected = True
    calls = {}

    async def fake_establish_connection(client_class, ble_device, name, **kwargs):
        calls["client_class"] = client_class
        calls["device"] = ble_device
        calls["name"] = name
        calls["kwargs"] = kwargs
        return fake_client

    monkeypatch.setattr(
        ble_module.bluetooth,
        "async_ble_device_from_address",
        lambda hass, address, connectable=True: device,
    )
    monkeypatch.setattr(ble_module, "establish_connection", fake_establish_connection)

    client = GvmBleClient(
        "94:C9:60:B6:CC:87", hass=SimpleNamespace(), name="BT_LED"
    )
    await client.async_connect()

    assert calls["client_class"] is BleakClientWithServiceCache
    assert calls["device"] is device
    assert calls["name"] == "BT_LED"
    assert calls["kwargs"]["max_attempts"] == 3
    assert fake_client.connect_calls == 0
    assert fake_client.writes == ["4C5409000053000001009474\r\n"]
