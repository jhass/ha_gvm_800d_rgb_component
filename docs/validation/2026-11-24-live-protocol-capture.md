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
4C540900315700060101D5DF   mode 01 (color temperature)
4C540900315700060102E5BC   mode 02 (color)
4C540900315700060103F59D   mode 03 (effect)
4C54090031570007010F0321   scene 0F (Hue Loop)
4C54090031570008011A6D84   speed 0x1A (2600 ms)
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
- [x] Direct BLE handshake reads device identity and CCT bounds.
- [x] Direct on/off, brightness, CCT, hue, and saturation match app behavior.
- [x] HA entity connects to `BT_LED` and reads handshake data.
- [x] HA on/off, brightness, CCT, hue, and saturation match app behavior.
- [x] HA receives state notifications, marks the entity unavailable on BLE loss, and reconnects after the light returns.
- [x] App `rgb31` scene list decoded into 18 labels for command `07`.
- [x] App speed values `0x02`–`0x2D` decoded as 200–4500 ms for command `08`.
- [ ] HA mode, scene, and speed entities validated on the physical light.

## Feature mapping and exclusions

The direct GATT command set covers power, brightness, CCT, hue, saturation, mode, built-in scene, and effect speed. The app uses these commands from `MainActivity` and `ColorfulActivity`, and the captured frames above confirm the value ranges used by device type `31`.

The app's custom-effect, source-matching, zone-dimming, and group screens send arrays through `ThingUtil.publishDpsDevice()` using Tuya/Thingclips device or group state. Those features are not reproducible from the direct BLE GATT commands captured here and are intentionally excluded. Phone-microphone music effects are also excluded because they depend on phone audio input. The `rgb33` scene list adds two extra strobe scenes that are not present on this `rgb31` light, so they are not exposed.

## Local BLE results

Validation used `tools/local_ble_probe.py` against the physical light from the local macOS Bluetooth stack. The phone app was closed and HA was not holding the connection.

The first handshake query produced only a state notification. The light returned the handshake response after the second query:

```text
4C540A00315300000220389378
```

Decoded as device ID `00`, device type `31`, CCT minimum `3200 K`, and CCT maximum `5600 K`. This matches the app's `resloveHandData` parser, so the integration repeats the handshake query once per second until a `53` response arrives.

A representative state notification:

```text
4C540E003103010915343949010F1D9CD3
payload 010915343949010F1D
```

Decoded as power on, brightness `24`, CCT `5200 K`, hue `285°`, saturation `73`, mode `01`, scene detail `15`, and speed `2900 ms`.

Captured control frames were written as raw bytes with the `0xFF` terminator. Observed state changes:

```text
4C540900315700000100775E   power off -> power False
4C540900315700000101677F   power on  -> power True
4C5409003157000201188A07   brightness 0x18 -> brightness 24
4C5409003157000301200A6C   CCT 0x20 -> 3200 K
4C540900315700040132BD8F   hue 0x32 -> 250°
4C54090031570005012B09A7   saturation 0x2B -> 43
```

HA validation was completed on the HA host after reloading the integration. All controls changed the physical light and the entity state updated from notifications. A power-cycle marked the entity unavailable promptly and it became available again automatically after the light returned, because the BLE client now registers `disconnected_callback` with `bleak_retry_connector.establish_connection()`.

## Local BLE probe

`tools/local_ble_probe.py` uses the local machine's BLE stack instead of Home Assistant. It is useful for isolating protocol problems from HA integration problems.

Before each run:

1. Power-cycle the light. It can stop advertising after being on for a while.
2. Close the GVM phone app.
3. Unload or disable the HA integration so it does not hold the single BLE connection.
4. Keep the light within a few metres of the machine running the probe.

Run the handshake probe:

```bash
.venv/bin/python tools/local_ble_probe.py
```

Send one captured command after the handshake:

```bash
.venv/bin/python tools/local_ble_probe.py --frame 4C540900315700000101677F
```

Build and send a command from bytes:

```bash
.venv/bin/python tools/local_ble_probe.py --cmd 0x02 --value 0x18
```

The probe writes raw bytes with the app's `0xFF` terminator and `WRITE_NO_RESPONSE`, then prints every notification as raw hex and decoded text. It repeats the handshake query once per second until the light returns a `53` response; the physical light responds on the second query. Use `--listen-seconds 8` after a command because the first notification can be a periodic state report from before the write.

Effect command validation on 2026-11-24:

```text
4C540900315700060103F59D   mode 03
4C54090031570007010F0321   scene 0F -> mode 03, scene_detail 15 (Hue Loop)
4C54090031570008011A6D84   speed 0x1A -> speed_ms 2600
```

The mode/scene/speed mappings are confirmed from the local BLE stack with the GVM phone app closed. Home Assistant entity validation for these new controls is still pending.
