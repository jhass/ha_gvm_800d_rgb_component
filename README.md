# GVM 800D RGB for Home Assistant

Direct local Bluetooth control for the GVM 800D RGB light that advertises as `BT_LED`.

No GVM cloud account, Tuya account, or MQTT bridge is required.

## Features

- On/off and brightness
- Color temperature with the light's reported Kelvin range
- HS and RGB color
- Device notifications for power, brightness, color, mode, scene, and effect speed
- Automatic reconnect after the light drops BLE
- 18 built-in `rgb31` scenes as a Home Assistant select entity
- Effect speed as a Home Assistant number entity (200–4500 ms)
- Mode select for color temperature, color, and effect modes
- Setup from a scanner-driven list of nearby lights; manual address entry remains available

The app's microphone-reactive music effects, cloud-managed custom effects, zone dimming, groups, and the extra `rgb33`-only scenes are not exposed because they are not available through the light's direct GATT command set.

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

Open **Settings → Devices & services → Add integration** and select **GVM 800D RGB**. The setup flow lists nearby advertisements whose name contains `BT_LED`, plus devices advertising the GVM GATT service UUID, so you do not need to know the Bluetooth address. Choose **Rescan for lights** if the light is missing, or **Enter MAC address manually** as a fallback. Manual entry also accepts a macOS-style BLE UUID.

The light supports one BLE connection at a time. Close the GVM phone app before connecting it to Home Assistant.

## Entities

- **Light:** power, brightness, color temperature, HS/RGB color
- **Selects:** mode (`Color temperature`, `Color`, `Effect`) and the 18 built-in scenes
- **Number:** effect speed in milliseconds

Choosing a scene or changing effect speed switches the light into its effect mode first, matching the app's command sequence. Entity names and options follow the values reported by the Android app protocol.

## Troubleshooting

- **No lights found:** power-cycle the light, move it closer to the Bluetooth adapter, and reopen the setup form. **Rescan for lights** refreshes Home Assistant's discovery cache; it does not start an active scan.
- **Failed setup or handshake timeout:** close the phone app and make sure no other integration is holding the light's BLE connection.
- **Entity unavailable after power-cycle:** this is expected briefly. The integration marks it unavailable and reconnects automatically when the light returns.

## Validation

See [docs/validation/2026-11-24-live-protocol-capture.md](docs/validation/2026-11-24-live-protocol-capture.md) for reverse-engineering evidence, captured frames, and live validation results.

`tools/local_ble_probe.py` can validate the protocol from a machine with a Bluetooth adapter without Home Assistant.
