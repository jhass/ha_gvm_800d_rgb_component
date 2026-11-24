import asyncio

from custom_components.gvm_800d.ble import GvmBleClient
from custom_components.gvm_800d.const import CHARACTERISTIC_UUID


class FakeBleakClient:
    def __init__(self, address):
        self.address = address
        self.connected = False
        self.writes = []
        self.notify_callback = None

    async def connect(self):
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

    def factory(mac):
        holder["client"] = FakeBleakClient(mac)
        return holder["client"]

    return holder, factory


async def test_connect_sends_handshake():
    holder, factory = make_client()
    client = GvmBleClient("94:C9:60:B6:CC:87", client_factory=factory)
    await client.async_connect()
    assert holder["client"].connected is True
    assert holder["client"].writes == ["4C5409000053000001009474\r\n"]


async def test_send_command_writes_captured_frame():
    holder, factory = make_client()
    client = GvmBleClient("94:C9:60:B6:CC:87", client_factory=factory)
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
        client_factory=factory,
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
