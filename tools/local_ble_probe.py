#!/usr/bin/env python3
"""Probe a GVM light directly from the local BLE stack."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from bleak import BleakClient, BleakScanner

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.gvm_800d.const import (  # noqa: E402
    CHARACTERISTIC_UUID,
    HANDSHAKE_FRAME,
    SERVICE_UUID,
)
from custom_components.gvm_800d.ble import build_command_frame  # noqa: E402

TERMINATOR = b"\xff"


def normalize_hex(value: str) -> str:
    """Return an uppercase hex string without separators."""
    return value.replace(" ", "").replace("-", "").upper()


def frame_payload(frame: str) -> bytes:
    """Return the raw bytes the Android app writes for a hex frame."""
    return bytes.fromhex(normalize_hex(frame)) + TERMINATOR


async def find_device(name: str, timeout: float):
    """Find a connectable device by advertised name or GVM service UUID."""
    devices = await BleakScanner.discover(timeout=timeout)
    name_needle = name.lower()
    matches = []
    for device in devices:
        device_name = (device.name or "").lower()
        services = {
            str(uuid)
            for uuid in (getattr(device.details, "service_uuids", None) or [])
        }
        if name_needle in device_name or SERVICE_UUID in services:
            matches.append(device)
    return matches, devices


async def probe(args: argparse.Namespace) -> int:
    """Connect, subscribe, send the handshake, and optionally send a command."""
    matches, devices = await find_device(args.name, args.timeout)
    if args.device:
        device = next((d for d in devices if d.address == args.device), None)
        if device is None:
            device = next(
                (d for d in matches if d.address.lower() == args.device.lower()), None
            )
    elif len(matches) == 1:
        device = matches[0]
    else:
        device = None

    if device is None:
        print(f"No GVM light found among {len(devices)} BLE advertisements.")
        print("Power-cycle the light, close the phone app, unload HA, and retry.")
        for candidate in devices:
            print(f"  {candidate.address} {candidate.name!r}")
        return 1

    print(f"Connecting to {device.address} ({device.name!r})")
    notification = asyncio.Event()
    client = BleakClient(device)

    def on_notify(_sender, data: bytearray) -> None:
        raw = bytes(data)
        print(f"NOTIFY raw={raw.hex(' ').upper()} text={raw!r}")
        notification.set()

    try:
        await client.connect()
        await client.start_notify(CHARACTERISTIC_UUID, on_notify)
        await client.write_gatt_char(
            CHARACTERISTIC_UUID, frame_payload(HANDSHAKE_FRAME), response=False
        )
        print(f"WRITE  {HANDSHAKE_FRAME}")
        try:
            await asyncio.wait_for(notification.wait(), args.handshake_timeout)
        except TimeoutError:
            print("No notification after handshake query.")
        else:
            print("Handshake notification received.")

        if args.frame or args.cmd is not None:
            notification.clear()
            frame = args.frame or build_command_frame(
                args.device_id, args.device_type, args.cmd, args.value
            )
            await client.write_gatt_char(
                CHARACTERISTIC_UUID, frame_payload(frame), response=False
            )
            print(f"WRITE  {normalize_hex(frame)}")
            try:
                await asyncio.wait_for(notification.wait(), args.handshake_timeout)
            except TimeoutError:
                print("No notification after command.")
    finally:
        await client.disconnect()
    return 0


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="BT_LED", help="advertised device name")
    parser.add_argument(
        "--device", help="BLE address/UUID from a prior scan to connect to directly"
    )
    parser.add_argument(
        "--timeout", type=float, default=15.0, help="scan duration in seconds"
    )
    parser.add_argument(
        "--handshake-timeout",
        type=float,
        default=5.0,
        help="notification wait in seconds",
    )
    parser.add_argument("--device-id", default="00", help="GVM device ID byte")
    parser.add_argument("--device-type", default="31", help="GVM device type byte")
    parser.add_argument("--cmd", type=lambda value: int(value, 0), help="command byte")
    parser.add_argument(
        "--value", type=lambda value: int(value, 0), default=0, help="command value"
    )
    parser.add_argument("--frame", help="complete hex frame to write after handshake")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(probe(parse_args())))
