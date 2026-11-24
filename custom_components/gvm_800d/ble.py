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
