# GVM 800D RGB for Home Assistant

Direct local Bluetooth control for the GVM 800D RGB light that advertises as `BT_LED`.

No GVM cloud account, Tuya account, or MQTT bridge is required.

## Features

- On/off and brightness
- Color temperature with the light's reported Kelvin range
- HS and RGB color
- Device notifications for power, brightness, color, and mode
- Automatic reconnect after the light drops BLE
- Effects, scenes, speed, and mode controls via Home Assistant select entities
- Setup from a scanner-driven list of nearby lights; manual MAC entry remains available

Microphone-reactive music effects are not implemented because they require the phone app's microphone input.

## Installation

### HACS

1. Add this repository to HACS as a custom repository of type **Integration**.
2. Install **GVM 800D RGB**.
3. Restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration** and choose **GVM 800D RGB**.

### Manual

Copy `custom_components/gvm_800d` into your Home Assistant `config/custom_components` directory and restart Home Assistant.

## Setup

Power-cycle the light if it has been on for a while; these lights can stop advertising after extended uptime.

Open **Settings → Devices & services → Add integration** and select **GVM 800D RGB**. The setup flow lists nearby `BT_LED` advertisements so you do not need to know the MAC address. Choose **Rescan for lights** if the light is missing, or **Enter MAC address manually** as a fallback.

The light supports one BLE connection at a time. Close the GVM phone app before connecting it to Home Assistant.

## Entities

- **Light:** power, brightness, color temperature, HS/RGB color
- **Selects:** effect/scene, mode, and effect speed

Entity names and options follow the values reported by the Android app protocol.

## Troubleshooting

- **No lights found:** power-cycle the light, move it closer to the Bluetooth adapter, and rescan.
- **Failed setup or handshake timeout:** close the phone app and make sure no other integration is holding the light's BLE connection.
- **Entity unavailable after power-cycle:** this is expected briefly. The integration marks it unavailable and reconnects automatically when the light returns.

## Validation

See [docs/validation/2026-11-24-live-protocol-capture.md](docs/validation/2026-11-24-live-protocol-capture.md) for reverse-engineering evidence, captured frames, and live validation results.

`tools/local_ble_probe.py` can validate the protocol from a machine with a Bluetooth adapter without Home Assistant.
