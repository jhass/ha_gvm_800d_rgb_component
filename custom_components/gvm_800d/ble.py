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
