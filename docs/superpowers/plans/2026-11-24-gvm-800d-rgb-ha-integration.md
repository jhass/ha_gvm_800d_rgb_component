# GVM 800D RGB Home Assistant Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a HACS/Marketplace-compatible Home Assistant integration that directly controls and reads state from the GVM 800D RGB light over BLE.

**Architecture:** A `bleak`-based transport isolates the GVM GATT protocol, a coordinator owns connection lifecycle and command coalescing, and a single `LightEntity` exposes power, brightness, HS/RGB color, and CCT. Home Assistant config flow handles Bluetooth discovery and manual MAC entry.

**Tech Stack:** Python 3.12+, Home Assistant 2024.6+, `bleak` via HA Bluetooth integration, pytest, pytest-homeassistant-custom-component.

---

## File structure

```text
custom_components/gvm_800d/__init__.py    coordinator and setup/unload
custom_components/gvm_800d/ble.py         protocol primitives and BLE client
custom_components/gvm_800d/config_flow.py discovery and manual MAC setup
custom_components/gvm_800d/const.py       UUIDs, commands, limits
custom_components/gvm_800d/light.py       LightEntity
custom_components/gvm_800d/manifest.json  HA integration metadata
custom_components/gvm_800d/strings.json   config flow strings
custom_components/gvm_800d/translations/en.json
hacs.json                                 HACS/Marketplace metadata
README.md                                 installation and validation docs
LICENSE                                   MIT license
tests/conftest.py                         pytest HA fixtures
tests/test_protocol.py                    CRC, frame, parser tests
tests/test_ble_client.py                  BLE client tests with fake client
tests/test_coordinator.py                 coordinator tests
tests/test_config_flow.py                 config flow tests
tests/test_light.py                       light entity tests
tests/test_metadata.py                    manifest/HACS metadata tests
docs/validation/2026-11-24-live-protocol-capture.md
requirements_test.txt
.gitignore
```

## Task 1: Repository scaffolding and metadata

**Files:**
- Create: `.gitignore`
- Create: `requirements_test.txt`
- Create: `hacs.json`
- Create: `README.md`
- Create: `LICENSE`
- Create: `custom_components/gvm_800d/manifest.json`
- Create: `custom_components/gvm_800d/__init__.py`
- Create: `tests/__init__.py`
- Test: `tests/test_metadata.py`

- [ ] **Step 1: Write the failing metadata test**

```python
# tests/test_metadata.py
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_manifest():
    data = json.loads((ROOT / "custom_components/gvm_800d/manifest.json").read_text())
    assert data["domain"] == "gvm_800d"
    assert data["name"] == "GVM 800D RGB"
    assert data["config_flow"] is True
    assert data["dependencies"] == ["bluetooth"]
    assert data["iot_class"] == "local_push"
    assert (
        data["bluetooth"][0]["match"]["service_uuid"]
        == "00010203-0405-0607-0809-0a0b0c0d1910"
    )


def test_hacs_json():
    data = json.loads((ROOT / "hacs.json").read_text())
    assert data["name"] == "GVM 800D RGB"
    assert data["render_readme"] is True
    assert data["homeassistant"] == "2024.6.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_metadata.py -v`
Expected: FAIL with `FileNotFoundError` for `custom_components/gvm_800d/manifest.json` or `hacs.json`.

- [ ] **Step 3: Create the package and metadata files**

```python
# custom_components/gvm_800d/__init__.py
"""GVM 800D RGB integration."""
```

```python
# tests/__init__.py
```

```gitignore
# .gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.venv/
venv/
.DS_Store
GVM_LED_V1.8.4.apk
```

```text
# requirements_test.txt
homeassistant==2024.6.0
pytest>=8.0
pytest-asyncio>=0.23
pytest-homeassistant-custom-component>=0.13.0
```

```json
// hacs.json
{
  "name": "GVM 800D RGB",
  "render_readme": true,
  "homeassistant": "2024.6.0",
  "zip_release": false
}
```

```json
// custom_components/gvm_800d/manifest.json
{
  "domain": "gvm_800d",
  "name": "GVM 800D RGB",
  "codeowners": ["@jhass"],
  "config_flow": true,
  "dependencies": ["bluetooth"],
  "documentation": "https://github.com/jhass/ha_gvm_800d_rgb_component",
  "homeassistant": "2024.6.0",
  "integration_type": "device",
  "iot_class": "local_push",
  "issue_tracker": "https://github.com/jhass/ha_gvm_800d_rgb_component/issues",
  "bluetooth": [
    {
      "match": {
        "service_uuid": "00010203-0405-0607-0809-0a0b0c0d1910"
      }
    }
  ],
  "version": "0.1.0"
}
```

```markdown
<!-- README.md -->
# GVM 800D RGB for Home Assistant

Direct BLE control for the GVM 800D RGB light that advertises as `BT_LED`.

## Features

- On/off
- Brightness
- HS and RGB color
- Color temperature
- State from device notifications
- Automatic reconnect

Effects, zone dimming, device-level groups, and microphone-reactive modes are not included.

## Installation

1. Add this repository to HACS as a custom repository of type **Integration**.
2. Install **GVM 800D RGB**.
3. Restart Home Assistant.
4. In **Settings → Devices & services**, add **GVM 800D RGB**. The integration discovers `BT_LED` advertisements, or you can enter the MAC address manually.

The light can maintain one BLE connection at a time. Disconnect it from the GVM phone app before connecting it to Home Assistant.

## Configuration

- **MAC address:** Bluetooth MAC address, for example `94:C9:60:B6:CC:87`.

No cloud account is required.

## Validation

See [docs/validation/2026-11-24-live-protocol-capture.md](docs/validation/2026-11-24-live-protocol-capture.md) for the reverse-engineering evidence and live capture.
```

```text
# LICENSE
MIT License

Copyright (c) 2026 jhass

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_metadata.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add .gitignore requirements_test.txt hacs.json README.md LICENSE \
  custom_components/gvm_800d/__init__.py \
  custom_components/gvm_800d/manifest.json \
  tests/__init__.py tests/test_metadata.py
git commit -m "feat: scaffold HACS integration metadata"
```

## Task 2: Protocol constants, CRC, and frame builders

**Files:**
- Create: `custom_components/gvm_800d/const.py`
- Create: `custom_components/gvm_800d/ble.py`
- Test: `tests/test_protocol.py`

- [ ] **Step 1: Write the failing protocol tests**

```python
# tests/test_protocol.py
from custom_components.gvm_800d.ble import (
    build_ack_frame,
    build_command_frame,
    crc16_ccitt,
)


CAPTURED_FRAMES = [
    "4C5409000053000001009474",
    "4C540900315700060101D5DF",
    "4C540900315700000100775E",
    "4C5409003157000201188A07",
    "4C54090031570005012B09A7",
]


def test_crc_matches_captured_frames():
    for frame in CAPTURED_FRAMES:
        base, crc = frame[:-4], frame[-4:]
        assert f"{crc16_ccitt(bytes.fromhex(base)):04X}" == crc


def test_build_command_frame_matches_capture():
    assert build_command_frame("00", "31", 0x06, 0x01) == "4C540900315700060101D5DF"
    assert build_command_frame("00", "31", 0x00, 0x00) == "4C540900315700000100775E"


def test_build_ack_frame():
    assert build_ack_frame("00", "31", "01020520") == "4C540900314801020520E68F"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_protocol.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.gvm_800d.ble'`.

- [ ] **Step 3: Write constants**

```python
# custom_components/gvm_800d/const.py
"""Constants for the GVM 800D RGB integration."""

DOMAIN = "gvm_800d"
CONF_MAC = "mac"

SERVICE_UUID = "00010203-0405-0607-0809-0a0b0c0d1910"
CHARACTERISTIC_UUID = "00010203-0405-0607-0809-0a0b0c0d2b10"

HANDSHAKE_FRAME = "4C5409000053000001009474"
COMMAND_PREFIX = "4C5409"
COMMAND_MARKER = "5700"

CMD_POWER = 0x00
CMD_SCENE = 0x01
CMD_BRIGHTNESS = 0x02
CMD_COLOR_TEMP = 0x03
CMD_HUE = 0x04
CMD_SATURATION = 0x05
CMD_MODE = 0x06
CMD_SCENE_SELECT = 0x07
CMD_SPEED = 0x08

MODE_CCT = 0x01
MODE_COLOR = 0x02

PLATFORMS = ["light"]
```

- [ ] **Step 4: Write protocol primitives**

```python
# custom_components/gvm_800d/ble.py
"""GVM 800D RGB BLE protocol primitives and client."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from bleak import BleakClient

from .const import (
    CHARACTERISTIC_UUID,
    COMMAND_MARKER,
    COMMAND_PREFIX,
    HANDSHAKE_FRAME,
)


def _normalize_hex(value: str) -> str:
    """Return uppercase hex without separators."""
    return (
        value.replace(" ", "")
        .replace("-", "")
        .replace("\r", "")
        .replace("\n", "")
        .upper()
    )


def crc16_ccitt(data: bytes) -> int:
    """CRC-16/CCITT, polynomial 0x1021, init 0x0000."""
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def _with_crc(base: str) -> str:
    """Append the uppercase, zero-padded CRC to a hex frame."""
    return base + f"{crc16_ccitt(bytes.fromhex(base)):04X}"


def build_command_frame(device_id: str, device_type: str, cmd: int, value: int) -> str:
    """Build a 5700 control frame."""
    base = (
        f"{COMMAND_PREFIX}{device_id}{device_type}{COMMAND_MARKER}"
        f"{cmd:02X}01{value:02X}"
    )
    return _with_crc(base)


def build_ack_frame(device_id: str, device_type: str, payload_hex: str) -> str:
    """Build the 48 state acknowledgement frame."""
    payload = _normalize_hex(payload_hex)
    body = f"{device_id}{device_type}48{payload}"
    length = len(body) // 2 + 2
    return _with_crc(f"4C54{length:02X}{body}")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_protocol.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add custom_components/gvm_800d/const.py \
  custom_components/gvm_800d/ble.py tests/test_protocol.py
git commit -m "feat: add GVM CRC and frame builders"
```

## Task 3: Handshake and state parsers

**Files:**
- Modify: `custom_components/gvm_800d/ble.py`
- Test: `tests/test_protocol.py`

- [ ] **Step 1: Add failing parser tests**

Append to `tests/test_protocol.py`:

```python
from custom_components.gvm_800d.ble import parse_handshake, parse_state
```

```python
def test_parse_handshake():
    frame = "4C54090031530000001E6400020B"
    assert parse_handshake(frame) == {
        "device_id": "00",
        "device_type": "31",
        "cct_min": 3000,
        "cct_max": 10000,
    }


def test_parse_handshake_ignores_default_query():
    assert parse_handshake("4C5409000053000001009474") is None


def test_parse_state_8_char_payload():
    assert parse_state("01020520") == {
        "power": True,
        "scene": 2,
        "brightness": 5,
        "cct_kelvin": 3200,
    }


def test_parse_state_12_char_payload():
    assert parse_state("010205200103")["mode"] == "01"
    assert parse_state("010205200103")["scene_detail"] == 3


def test_parse_state_18_char_payload():
    state = parse_state("010205200A0E01030A")
    assert state["hue"] == 50
    assert state["saturation"] == 14
    assert state["mode"] == "01"
    assert state["scene_detail"] == 3
    assert state["speed_ms"] == 1000


def test_parse_state_rejects_unknown_length():
    assert parse_state("0102") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_protocol.py -v`
Expected: FAIL with `ImportError: cannot import name 'parse_handshake'`.

- [ ] **Step 3: Implement parsers**

Append to `custom_components/gvm_800d/ble.py`:

```python
def parse_handshake(frame: str) -> dict[str, Any] | None:
    """Parse a 53 handshake response into device identity and CCT bounds."""
    value = _normalize_hex(frame)
    if len(value) < 22 or value[10:12] != "53":
        return None
    if value == HANDSHAKE_FRAME:
        return None
    try:
        return {
            "device_id": value[6:8],
            "device_type": value[8:10],
            "cct_min": int(value[18:20], 16) * 100,
            "cct_max": int(value[20:22], 16) * 100,
        }
    except ValueError:
        return None


def parse_state(payload_hex: str) -> dict[str, Any] | None:
    """Parse the payload carried by a 03 state notification."""
    value = _normalize_hex(payload_hex)
    if len(value) not in (8, 12, 18):
        return None
    try:
        state: dict[str, Any] = {
            "power": value[0:2] == "01",
            "scene": int(value[2:4], 16),
            "brightness": int(value[4:6], 16),
            "cct_kelvin": int(value[6:8], 16) * 100,
        }
        if len(value) == 12:
            state["mode"] = value[8:10]
            state["scene_detail"] = int(value[10:12], 16)
        elif len(value) == 18:
            state.update(
                {
                    "hue": int(value[8:10], 16) * 5,
                    "saturation": int(value[10:12], 16),
                    "mode": value[12:14],
                    "scene_detail": int(value[14:16], 16),
                    "speed_ms": int(value[16:18], 16) * 100,
                }
            )
        return state
    except ValueError:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_protocol.py -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add custom_components/gvm_800d/ble.py tests/test_protocol.py
git commit -m "feat: parse GVM handshake and state frames"
```

## Task 4: BLE client transport

**Files:**
- Modify: `custom_components/gvm_800d/ble.py`
- Test: `tests/test_ble_client.py`

- [ ] **Step 1: Write the failing BLE client test**

```python
# tests/test_ble_client.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_ble_client.py -v`
Expected: FAIL with `ImportError: cannot import name 'GvmBleClient'`.

- [ ] **Step 3: Implement the BLE client**

Append to `custom_components/gvm_800d/ble.py`:

```python
class GvmBleError(Exception):
    """Raised when GVM BLE communication fails."""


class GvmBleClient:
    """Own a single BLE connection to one GVM light."""

    def __init__(
        self,
        mac: str,
        on_handshake: Callable[[dict[str, Any]], None] | None = None,
        on_state: Callable[[dict[str, Any]], None] | None = None,
        client_factory: Callable[[str], BleakClient] | None = None,
    ) -> None:
        """Initialize the client."""
        self.mac = mac
        self._on_handshake = on_handshake
        self._on_state = on_state
        self._client_factory = client_factory or BleakClient
        self._client: BleakClient | None = None
        self._connected = False
        self._device_id = "00"
        self._device_type = "00"
        self._write_lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        """Return whether the client is connected."""
        return self._connected

    async def async_connect(self) -> None:
        """Connect, subscribe to notifications, and send the handshake query."""
        self._client = self._client_factory(self.mac)
        await self._client.connect()
        await self._client.start_notify(
            CHARACTERISTIC_UUID, self._handle_notification
        )
        self._connected = True
        await self._send_raw(HANDSHAKE_FRAME)

    async def async_disconnect(self) -> None:
        """Disconnect from the light."""
        self._connected = False
        if self._client is not None:
            await self._client.disconnect()

    async def send_command(self, cmd: int, value: int) -> None:
        """Send one control command with retries."""
        frame = build_command_frame(self._device_id, self._device_type, cmd, value)
        for attempt in range(3):
            try:
                await self._send_raw(frame)
                return
            except Exception as err:
                if attempt == 2:
                    raise GvmBleError(f"write failed for command {cmd:02X}") from err
                await asyncio.sleep(0.2)

    async def _send_raw(self, frame: str) -> None:
        """Write a hex frame, chunking only oversized frames."""
        if not self._connected or self._client is None:
            raise GvmBleError("not connected")
        async with self._write_lock:
            if len(frame) > 40:
                chunks = [frame[index : index + 20] for index in range(0, len(frame), 20)]
            else:
                chunks = [frame]
            for index, chunk in enumerate(chunks):
                await self._client.write_gatt_char(
                    CHARACTERISTIC_UUID,
                    (chunk + "\r\n").encode("ascii"),
                    response=True,
                )
                if index < len(chunks) - 1:
                    await asyncio.sleep(0.2)

    def _handle_notification(self, _sender: Any, data: bytearray) -> None:
        """Handle a GATT notification."""
        frame = _normalize_hex(bytes(data).decode("ascii", errors="ignore"))
        if len(frame) < 12:
            return
        marker = frame[10:12]
        if marker == "53":
            handshake = parse_handshake(frame)
            if handshake is None:
                return
            self._device_id = handshake["device_id"]
            self._device_type = handshake["device_type"]
            if self._on_handshake is not None:
                self._on_handshake(handshake)
        elif marker == "03":
            payload = frame[12:-4]
            state = parse_state(payload)
            if state is None:
                return
            if self._on_state is not None:
                self._on_state(state)
            ack = build_ack_frame(self._device_id, self._device_type, payload)
            asyncio.create_task(self._send_ack(ack))

    async def _send_ack(self, frame: str) -> None:
        """Send an acknowledgement without propagating background errors."""
        try:
            await self._send_raw(frame)
        except GvmBleError:
            pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_ble_client.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add custom_components/gvm_800d/ble.py tests/test_ble_client.py
git commit -m "feat: add serialized GVM BLE client"
```

## Task 5: Coordinator and config entry lifecycle

**Files:**
- Modify: `custom_components/gvm_800d/__init__.py`
- Test: `tests/test_coordinator.py`

- [ ] **Step 1: Write the failing coordinator test**

```python
# tests/test_coordinator.py
import asyncio
from types import SimpleNamespace

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_coordinator.py -v`
Expected: FAIL with `ImportError: cannot import name 'GvmDeviceCoordinator'`.

- [ ] **Step 3: Implement the coordinator**

Replace `custom_components/gvm_800d/__init__.py` with:

```python
"""GVM 800D RGB integration."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .ble import GvmBleClient, GvmBleError
from .const import CONF_MAC, DOMAIN, PLATFORMS


class GvmDeviceCoordinator:
    """Coordinate one light connection and its Home Assistant listeners."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: GvmBleClient | None = None,
    ) -> None:
        """Initialize the coordinator for a config entry."""
        self.hass = hass
        self.entry = entry
        self.mac = entry.data[CONF_MAC]
        self.client = client or GvmBleClient(
            self.mac,
            on_handshake=self._on_handshake,
            on_state=self._on_state,
        )
        self.handshake: dict[str, Any] | None = None
        self.state: dict[str, Any] = {}
        self._available = False
        self._handshake_event = asyncio.Event()
        self._listeners: list[Callable[[], None]] = []
        self._pending: dict[int, int] = {}
        self._write_task: asyncio.Task[None] | None = None
        self._reconnect_task: asyncio.Task[None] | None = None

    @property
    def available(self) -> bool:
        """Return whether the light is connected."""
        return self._available

    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a state listener and return a remove callback."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def _notify_listeners(self) -> None:
        """Notify registered listeners of new state."""
        for listener in list(self._listeners):
            listener()

    def _on_handshake(self, handshake: dict[str, Any]) -> None:
        """Store handshake data and unblock setup."""
        self.handshake = handshake
        self._handshake_event.set()

    def _on_state(self, state: dict[str, Any]) -> None:
        """Store state and notify entities."""
        self.state.update(state)
        self._available = True
        self._notify_listeners()

    async def async_connect(self) -> None:
        """Connect and wait for a valid handshake."""
        self._handshake_event.clear()
        await self.client.async_connect()
        try:
            await asyncio.wait_for(self._handshake_event.wait(), 10)
        except TimeoutError as err:
            raise GvmBleError("handshake timeout") from err
        self._available = True
        self._notify_listeners()

    async def async_request(self, cmd: int, value: int) -> None:
        """Queue the latest value for a command."""
        self._pending[cmd] = value
        if self._write_task is None or self._write_task.done():
            self._write_task = asyncio.create_task(self._drain_writes())
        await self._write_task

    async def _drain_writes(self) -> None:
        """Write the latest queued value for each command."""
        while self._pending:
            pending = dict(self._pending)
            self._pending.clear()
            for cmd, value in pending.items():
                try:
                    await self.client.send_command(cmd, value)
                except Exception:
                    self._available = False
                    self._notify_listeners()
                    self._schedule_reconnect()
                    return

    def _schedule_reconnect(self) -> None:
        """Start a reconnect loop if one is not already running."""
        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Reconnect with capped exponential backoff."""
        delay = 5
        while True:
            await asyncio.sleep(delay)
            try:
                await self.async_connect()
                return
            except Exception:
                delay = min(delay * 2, 30)

    async def async_shutdown(self) -> None:
        """Cancel background work and disconnect."""
        for task in (self._write_task, self._reconnect_task):
            if task is not None and not task.done():
                task.cancel()
        await self.client.async_disconnect()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GVM 800D RGB from a config entry."""
    coordinator = GvmDeviceCoordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    try:
        await coordinator.async_connect()
    except Exception as err:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        raise ConfigEntryNotReady from err
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a GVM 800D RGB config entry."""
    coordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.async_shutdown()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_coordinator.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add custom_components/gvm_800d/__init__.py tests/test_coordinator.py
git commit -m "feat: add coordinator and entry lifecycle"
```

## Task 6: Config flow

**Files:**
- Create: `custom_components/gvm_800d/config_flow.py`
- Test: `tests/test_config_flow.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write the failing config-flow test**

```python
# tests/conftest.py
import pytest

pytest_plugins = "pytest_homeassistant_custom_component.plugins"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in all tests."""
    yield
```

```python
# tests/test_config_flow.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_config_flow.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.gvm_800d.config_flow'`.

- [ ] **Step 3: Implement the config flow**

```python
# custom_components/gvm_800d/config_flow.py
"""Config flow for GVM 800D RGB."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_MAC, DOMAIN


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_config_flow.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py custom_components/gvm_800d/config_flow.py tests/test_config_flow.py
git commit -m "feat: add GVM config flow"
```

## Task 7: Light entity

**Files:**
- Create: `custom_components/gvm_800d/light.py`
- Test: `tests/test_light.py`

- [ ] **Step 1: Write the failing light tests**

```python
# tests/test_light.py
import colorsys
from types import SimpleNamespace

from homeassistant.components.light import ATTR_COLOR_TEMP_KELVIN, ATTR_HS_COLOR, ColorMode

from custom_components.gvm_800d.const import (
    CMD_BRIGHTNESS,
    CMD_COLOR_TEMP,
    CMD_HUE,
    CMD_MODE,
    CMD_POWER,
    CMD_SATURATION,
    MODE_CCT,
    MODE_COLOR,
)
from custom_components.gvm_800d.light import GvmLight


class FakeCoordinator:
    def __init__(self):
        self.available = True
        self.mac = "94:C9:60:B6:CC:87"
        self.handshake = {"cct_min": 3000, "cct_max": 10000}
        self.state = {"power": False}
        self.calls = []
        self.listeners = []

    def async_add_listener(self, listener):
        self.listeners.append(listener)
        return lambda: None

    async def async_request(self, cmd, value):
        self.calls.append((cmd, value))


def make_light():
    coordinator = FakeCoordinator()
    entry = SimpleNamespace(title="GVM 800D RGB")
    return GvmLight(coordinator, entry), coordinator


def test_reports_state():
    light, coordinator = make_light()
    coordinator.state = {
        "power": True,
        "brightness": 50,
        "hue": 180,
        "saturation": 80,
        "cct_kelvin": 5600,
    }
    assert light.is_on is True
    assert light.brightness == 128
    assert light.hs_color == (180, 80)
    assert light.color_temp_kelvin == 5600
    assert light.min_color_temp_kelvin == 3000
    assert light.max_color_temp_kelvin == 10000
    assert ColorMode.HS in light.supported_color_modes
    assert ColorMode.RGB in light.supported_color_modes
    assert ColorMode.COLOR_TEMP in light.supported_color_modes


async def test_turn_on_with_hs_color():
    light, coordinator = make_light()
    await light.async_turn_on(**{ATTR_HS_COLOR: (180, 80)})
    assert (CMD_POWER, 1) in coordinator.calls
    assert (CMD_MODE, MODE_COLOR) in coordinator.calls
    assert (CMD_HUE, 36) in coordinator.calls
    assert (CMD_SATURATION, 80) in coordinator.calls
    assert light.color_mode is ColorMode.HS


async def test_turn_on_with_color_temp():
    light, coordinator = make_light()
    await light.async_turn_on(**{ATTR_COLOR_TEMP_KELVIN: 12000})
    assert (CMD_MODE, MODE_CCT) in coordinator.calls
    assert (CMD_COLOR_TEMP, 100) in coordinator.calls
    assert light.color_mode is ColorMode.COLOR_TEMP


async def test_turn_on_with_brightness_and_turn_off():
    light, coordinator = make_light()
    await light.async_turn_on(brightness=255)
    assert (CMD_BRIGHTNESS, 100) in coordinator.calls
    await light.async_turn_off()
    assert (CMD_POWER, 0) in coordinator.calls


def test_rgb_color_round_trip():
    light, coordinator = make_light()
    coordinator.state = {"power": True, "hue": 120, "saturation": 100}
    red, green, blue = light.rgb_color
    hue, saturation = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
    assert round(hue * 360 / 5) * 5 == 120
    assert round(saturation * 100) == 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_light.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.gvm_800d.light'`.

- [ ] **Step 3: Implement the light entity**

```python
# custom_components/gvm_800d/light.py
"""Light platform for GVM 800D RGB."""

from __future__ import annotations

import colorsys
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GvmDeviceCoordinator
from .const import (
    CMD_BRIGHTNESS,
    CMD_COLOR_TEMP,
    CMD_HUE,
    CMD_MODE,
    CMD_POWER,
    CMD_SATURATION,
    DOMAIN,
    MODE_CCT,
    MODE_COLOR,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the GVM light entity."""
    coordinator: GvmDeviceCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GvmLight(coordinator, entry)])


class GvmLight(LightEntity):
    """Represent one GVM 800D RGB light."""

    _attr_should_poll = False
    _attr_supported_color_modes = {
        ColorMode.HS,
        ColorMode.RGB,
        ColorMode.COLOR_TEMP,
    }

    def __init__(self, coordinator: GvmDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the light entity."""
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{coordinator.mac.replace(':', '')}_light"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            name=entry.title or "GVM 800D RGB",
            manufacturer="GVM",
            model="800D RGB",
        )
        self._active_mode = ColorMode.HS

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator updates."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    def _handle_coordinator_update(self) -> None:
        """Update HA state from coordinator state."""
        mode = self.coordinator.state.get("mode")
        if mode == "01":
            self._active_mode = ColorMode.COLOR_TEMP
        elif mode == "02":
            self._active_mode = ColorMode.HS
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return whether the light is connected."""
        return self.coordinator.available

    @property
    def is_on(self) -> bool:
        """Return whether the light is on."""
        return bool(self.coordinator.state.get("power", False))

    @property
    def brightness(self) -> int | None:
        """Return brightness in the Home Assistant 0-255 range."""
        brightness = self.coordinator.state.get("brightness")
        if brightness is None:
            return None
        return round(brightness * 255 / 100)

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return hue and saturation."""
        hue = self.coordinator.state.get("hue")
        saturation = self.coordinator.state.get("saturation")
        if hue is None or saturation is None:
            return None
        return float(hue), float(saturation)

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return RGB derived from the native HS state."""
        if self.hs_color is None:
            return None
        hue, saturation = self.hs_color
        red, green, blue = colorsys.hsv_to_rgb(hue / 360, saturation / 100, 1.0)
        return round(red * 255), round(green * 255), round(blue * 255)

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return color temperature in Kelvin."""
        return self.coordinator.state.get("cct_kelvin")

    @property
    def min_color_temp_kelvin(self) -> int:
        """Return the minimum supported color temperature."""
        if self.coordinator.handshake is None:
            return 2000
        return self.coordinator.handshake["cct_min"]

    @property
    def max_color_temp_kelvin(self) -> int:
        """Return the maximum supported color temperature."""
        if self.coordinator.handshake is None:
            return 6500
        return self.coordinator.handshake["cct_max"]

    @property
    def color_mode(self) -> ColorMode:
        """Return the active color mode."""
        return self._active_mode

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light or apply requested attributes."""
        if not self.is_on:
            await self.coordinator.async_request(CMD_POWER, 1)

        brightness = kwargs.get(ATTR_BRIGHTNESS)
        if brightness is not None:
            await self.coordinator.async_request(
                CMD_BRIGHTNESS, round(brightness * 100 / 255)
            )

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            value = self._kelvin_to_device(kwargs[ATTR_COLOR_TEMP_KELVIN])
            await self.coordinator.async_request(CMD_MODE, MODE_CCT)
            await self.coordinator.async_request(CMD_COLOR_TEMP, value)
            self._active_mode = ColorMode.COLOR_TEMP
        elif ATTR_HS_COLOR in kwargs:
            hue, saturation = kwargs[ATTR_HS_COLOR]
            hue_byte, saturation_byte = self._hs_to_device(hue, saturation)
            await self.coordinator.async_request(CMD_MODE, MODE_COLOR)
            await self.coordinator.async_request(CMD_HUE, hue_byte)
            await self.coordinator.async_request(CMD_SATURATION, saturation_byte)
            self._active_mode = ColorMode.HS
        elif ATTR_RGB_COLOR in kwargs:
            hue, saturation = self._rgb_to_hs(kwargs[ATTR_RGB_COLOR])
            hue_byte, saturation_byte = self._hs_to_device(hue, saturation)
            await self.coordinator.async_request(CMD_MODE, MODE_COLOR)
            await self.coordinator.async_request(CMD_HUE, hue_byte)
            await self.coordinator.async_request(CMD_SATURATION, saturation_byte)
            self._active_mode = ColorMode.RGB

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self.coordinator.async_request(CMD_POWER, 0)

    @staticmethod
    def _hs_to_device(hue: float, saturation: float) -> tuple[int, int]:
        """Convert HA HS values to device bytes."""
        hue_byte = round((hue % 360) / 5) % 76
        saturation_byte = max(0, min(100, round(saturation)))
        return hue_byte, saturation_byte

    @staticmethod
    def _rgb_to_hs(rgb: tuple[int, int, int]) -> tuple[float, float]:
        """Convert RGB to HS."""
        red, green, blue = (channel / 255 for channel in rgb)
        hue, saturation, _value = colorsys.rgb_to_hsv(red, green, blue)
        return hue * 360, saturation * 100

    def _kelvin_to_device(self, kelvin: int) -> int:
        """Convert Kelvin to the device's Kelvin/100 byte."""
        clamped = max(self.min_color_temp_kelvin, min(self.max_color_temp_kelvin, kelvin))
        return round(clamped / 100)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_light.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add custom_components/gvm_800d/light.py tests/test_light.py
git commit -m "feat: add GVM light entity"
```

## Task 8: Translations, validation record, and metadata test update

**Files:**
- Create: `custom_components/gvm_800d/strings.json`
- Create: `custom_components/gvm_800d/translations/en.json`
- Create: `docs/validation/2026-11-24-live-protocol-capture.md`
- Modify: `tests/test_metadata.py`

- [ ] **Step 1: Add the failing translation metadata test**

Append to `tests/test_metadata.py`:

```python
def test_translations():
    strings = json.loads(
        (ROOT / "custom_components/gvm_800d/strings.json").read_text()
    )
    english = json.loads(
        (ROOT / "custom_components/gvm_800d/translations/en.json").read_text()
    )
    assert strings == english
    assert strings["config"]["step"]["user"]["data"]["mac"] == "MAC address"
    assert "invalid_mac" in strings["config"]["error"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_metadata.py -v`
Expected: FAIL with `FileNotFoundError` for `strings.json`.

- [ ] **Step 3: Write strings and translations**

```json
// custom_components/gvm_800d/strings.json
{
  "config": {
    "step": {
      "user": {
        "title": "Connect to GVM 800D RGB",
        "description": "Enter the Bluetooth MAC address of your BT_LED light.",
        "data": {
          "mac": "MAC address"
        }
      },
      "bluetooth_confirm": {
        "title": "Connect to {name}?",
        "description": "Found {name} at {mac}. Continue with this light?"
      }
    },
    "error": {
      "invalid_mac": "Enter a valid MAC address."
    },
    "abort": {
      "already_configured": "This light is already configured.",
      "cannot_connect": "Could not connect to the light.",
      "unsupported_device": "This device is not a supported GVM light."
    }
  }
}
```

```json
// custom_components/gvm_800d/translations/en.json
{
  "config": {
    "step": {
      "user": {
        "title": "Connect to GVM 800D RGB",
        "description": "Enter the Bluetooth MAC address of your BT_LED light.",
        "data": {
          "mac": "MAC address"
        }
      },
      "bluetooth_confirm": {
        "title": "Connect to {name}?",
        "description": "Found {name} at {mac}. Continue with this light?"
      }
    },
    "error": {
      "invalid_mac": "Enter a valid MAC address."
    },
    "abort": {
      "already_configured": "This light is already configured.",
      "cannot_connect": "Could not connect to the light.",
      "unsupported_device": "This device is not a supported GVM light."
    }
  }
}
```

- [ ] **Step 4: Write the validation record**

```markdown
<!-- docs/validation/2026-11-24-live-protocol-capture.md -->
# Live protocol capture — 2026-11-24

## Device

- App: `GVM_LED_V1.8.4.apk`, version code 105
- Bluetooth name: `BT_LED`
- MAC: `94:C9:60:B6:CC:87`
- Connection mode: direct Bluetooth, no cloud account
- GATT service: `00010203-0405-0607-0809-0a0b0c0d1910`
- GATT characteristic: `00010203-0405-0607-0809-0a0b0c0d2b10`

## Evidence

The Android app was analyzed with REA. `ControlUtil.controlDev` builds frames as:

```text
4C5409 <devID> <devType> 5700 <cmd> 01 <value> <CRC16>
```

CRC-16 uses polynomial `0x1021` and initial value `0x0000`. Captured frames include:

```text
4C5409000053000001009474   handshake query
4C540900315700060101D5DF   mode 01
4C540900315700000100775E   power off
4C540900315700000101677F   power on
4C5409003157000201188A07   brightness 0x18
4C5409003157000301200A6C   CCT 0x20 (3200 K)
4C540900315700040132BD8F   hue 0x32 (50 * 5 degrees)
4C54090031570005012B09A7   saturation 0x2b
```

State notifications are parsed from payloads of 8, 12, or 18 hex characters after the 12-character header and before the 4-character CRC. Device type `31` uses the 18-character RGB state payload.

## Live validation checklist

- [x] ADB logcat captured 1,076 outbound frames while exercising the app.
- [x] CRC verified offline against captured frames.
- [x] Direct GVM BLE service and characteristic identified.
- [x] App handshake query identified: `4C5409000053000001009474`.
- [ ] HA connects to `BT_LED` and reads handshake data.
- [ ] HA on/off, brightness, CCT, hue, and saturation match app behavior.
- [ ] HA receives state notifications and reconnects after BLE loss.

The last three items are completed during implementation validation with the physical light.
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_metadata.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add custom_components/gvm_800d/strings.json \
  custom_components/gvm_800d/translations/en.json \
  docs/validation/2026-11-24-live-protocol-capture.md tests/test_metadata.py
git commit -m "docs: add translations and protocol validation record"
```

## Task 9: Full verification

**Files:** None. This task runs checks only.

- [ ] **Step 1: Run the full test suite**

Run: `python3 -m pytest -v`
Expected: PASS (24 tests total: 3 metadata + 9 protocol + 3 BLE client + 2 coordinator + 2 config flow + 5 light).

- [ ] **Step 2: Compile all Python files**

Run: `python3 -m compileall -q custom_components tests`
Expected: no output, exit code 0.

- [ ] **Step 3: Check working tree**

Run: `git status --short`
Expected: no output. The APK is ignored by `.gitignore`; if it appears, the `.gitignore` from Task 1 is missing and must be restored before continuing.

- [ ] **Step 4: Record live validation**

With the physical light:

1. Disconnect the GVM phone app from `BT_LED`.
2. Restart Home Assistant.
3. Add **GVM 800D RGB** via discovery or MAC `94:C9:60:B6:CC:87`.
4. Verify the entity appears and reports available.
5. Call `light.turn_on`, `light.turn_off`, brightness, `hs_color`, `rgb_color`, and `color_temp_kelvin`.
6. Confirm the light responds and HA state updates from notifications.
7. Power-cycle the light and confirm automatic reconnect.
8. Update the three unchecked checklist items in `docs/validation/2026-11-24-live-protocol-capture.md` and commit.

```bash
git add docs/validation/2026-11-24-live-protocol-capture.md
git commit -m "docs: record live HA validation"
```
