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

The probe writes raw bytes with the app's `0xFF` terminator and `WRITE_NO_RESPONSE`, then prints every notification as raw hex and decoded text.
