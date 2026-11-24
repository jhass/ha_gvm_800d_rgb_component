"""GVM 800D RGB BLE protocol primitives and client."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any, Callable

from bleak import BleakClient
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

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


class GvmBleError(Exception):
    """Raised when GVM BLE communication fails."""


class GvmBleClient:
    """Own a single BLE connection to one GVM light."""

    def __init__(
        self,
        mac: str,
        hass: HomeAssistant | None = None,
        name: str = "GVM 800D RGB",
        on_handshake: Callable[[dict[str, Any]], None] | None = None,
        on_state: Callable[[dict[str, Any]], None] | None = None,
        on_disconnect: Callable[[], None] | None = None,
        connect_factory: Callable[[], Awaitable[BleakClient]] | None = None,
    ) -> None:
        """Initialize the client."""
        self.mac = mac
        self._hass = hass
        self._name = name
        self._on_handshake = on_handshake
        self._on_state = on_state
        self._on_disconnect = on_disconnect
        self._connect_factory = connect_factory or self._async_establish_connection
        self._client: BleakClient | None = None
        self._connected = False
        self._intentional_disconnect = False
        self._device_id = "00"
        self._device_type = "31"
        self._write_lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        """Return whether the client is connected."""
        return self._connected

    async def async_connect(self) -> None:
        """Connect, subscribe to notifications, and send the handshake query."""
        self._intentional_disconnect = False
        self._client = await self._connect_factory()
        await self._client.start_notify(
            CHARACTERISTIC_UUID, self._handle_notification
        )
        self._connected = True
        await self.async_send_handshake()

    async def async_send_handshake(self) -> None:
        """Send the handshake query used to discover device identity."""
        await self._send_raw(HANDSHAKE_FRAME)

    async def _async_establish_connection(self) -> BleakClient:
        """Connect through Home Assistant with retry and service caching."""
        if self._hass is None:
            raise GvmBleError("Home Assistant instance is required for BLE connection")
        device = bluetooth.async_ble_device_from_address(
            self._hass, self.mac, connectable=True
        )
        if device is None:
            device = bluetooth.async_ble_device_from_address(
                self._hass, self.mac, connectable=False
            )
        if device is None:
            raise GvmBleError(
                f"{self.mac} is not visible to a connectable Bluetooth adapter"
            )
        return await establish_connection(
            BleakClientWithServiceCache,
            device,
            self._name,
            disconnected_callback=self._handle_disconnect,
            max_attempts=3,
        )

    def _handle_disconnect(self, _client: BleakClient) -> None:
        """Handle an unexpected BLE disconnection."""
        self._connected = False
        if self._intentional_disconnect:
            return
        if self._on_disconnect is not None:
            self._on_disconnect()

    async def async_disconnect(self) -> None:
        """Disconnect from the light."""
        self._intentional_disconnect = True
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
        """Write a hex frame as raw bytes with the app's 0xFF terminator."""
        if not self._connected or self._client is None:
            raise GvmBleError("not connected")
        payload = bytes.fromhex(frame) + b"\xff"
        async with self._write_lock:
            await self._client.write_gatt_char(
                CHARACTERISTIC_UUID,
                payload,
                response=False,
            )

    def _handle_notification(self, _sender: Any, data: bytearray) -> None:
        """Handle a GATT notification."""
        raw = bytes(data)
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            text = ""
        normalized_text = _normalize_hex(text)
        if normalized_text and all(
            char in "0123456789ABCDEF" for char in normalized_text
        ):
            frame = normalized_text
        else:
            frame = raw.hex().upper()
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
