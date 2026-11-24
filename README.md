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
