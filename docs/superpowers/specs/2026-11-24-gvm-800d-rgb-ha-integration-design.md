# GVM 800D RGB Home Assistant Integration — Design

Date: 2026-11-24
Status: Design approved; written spec awaiting user review

## 1. Context and goal

The user owns a GVM 800D RGB light that appears over Bluetooth as `BT_LED` (MAC `94:C9:60:B6:CC:87`) and pairs directly, without a GVM/Tuya cloud account. The GVM Android app `GVM_LED_V1.8.4.apk` was reverse engineered with REA, and its outbound frames were captured live from the connected phone via ADB logcat.

Goal: build a full custom Home Assistant integration, published in a HACS/Home Assistant Marketplace-compatible repository, that controls the light directly over BLE from Home Assistant.

### In scope for this spec

- HACS/Marketplace repository layout and metadata.
- Config flow using Bluetooth discovery plus manual MAC entry.
- Direct BLE transport: connect, handshake, notifications, CRC framing, serialized writes, reconnect.
- One Home Assistant `light` entity with power, brightness, HS/RGB color, and color temperature.
- State parsing from device notifications and optimistic updates.
- Tests and live validation against the physical light.

### Out of scope for this spec

- Effects, scenes, speed, zone dimming, and device-level groups. These are later phases.
- Phone-microphone music-reactive modes. The user explicitly does not want them.
- Tuya/SigMesh DPS path used by other app screens. The 800D RGB uses the custom GVM BLE path.
- Cloud accounts, login, and remote API access.

## 2. Protocol evidence

### 2.1 GATT

- Service: `00010203-0405-0607-0809-0a0b0c0d1910`
- Characteristic: `00010203-0405-0607-0809-0a0b0c0d2b10`
- The characteristic supports read, write, and notify.
- Writes use the Android default write type, equivalent to `bleak` writes with `response=True`.
- Notifications are enabled before the handshake.

### 2.2 Command frame

All control frames captured from the app are 12 bytes / 24 hex characters:

```text
4C 54 09 <devID> <devType> 57 00 <cmd> 01 <value> <CRC16>
```

Example: `4C540900315700060101D5DF` = mode `06`, value `01`.

- `<devID>` and `<devType>` are learned from the handshake response; live values were `00` and `31`.
- `01` after the command is a fixed separator in the app's `ControlUtil.controlDev`.
- `<value>` is one byte for every core command.
- CRC is CRC-16/CCITT with polynomial `0x1021`, init `0x0000`, no reflection, no final XOR, rendered uppercase and zero-padded to four hex characters.
- The CRC was verified offline against captured frames, including the handshake `4C5409000053000001009474`.

### 2.3 Command map

All values in this table are the hex byte written in the frame. Where a decimal range is given, the hex byte is the decimal value encoded in one byte.

| Byte | Meaning | Value encoding |
| --- | --- | --- |
| `00` | Power | `00` off, `01` on |
| `01` | Scene/preset | Decimal 1–12 from the app's number picker, encoded as `01`–`0C` |
| `02` | Brightness | Decimal 0–100 encoded as `00`–`64`; live slider produced `0D`–`52` |
| `03` | Color temperature | Kelvin / 100 encoded as a hex byte; clamp to handshake min/max |
| `04` | Hue | Decimal 0–75 in 5° steps, encoded as `00`–`4B` |
| `05` | Saturation | Decimal 0–100 encoded as `00`–`64`; live slider produced `14`–`64` |
| `06` | Mode | `01` CCT/white, `02` color/RGB, `03` also observed in UI |
| `07` | Scene selection | Single value `0F` observed; exact mapping deferred to phase 2 |
| `08` | Effect speed/time | Decimal value × 100 ms, encoded as a hex byte; live values `02`–`2C` |

Color flow from the app: mode `06 01` precedes CCT command `03`; mode `06 02` precedes hue command `04`. Saturation is then sent with `05`.

### 2.4 Handshake and state responses

The app sends `4C5409000053000001009474` to query the device. Notifications whose byte at hex offset `[10,12)` is `53` are handshake responses. The app ignores the exact default query frame and parses real handshake responses as:

- Device ID: hex `[6,8)`
- Device type: hex `[8,10)`
- CCT minimum: `int(hex[18,20), 16)` hundreds of Kelvin
- CCT maximum: `int(hex[20,22), 16)` hundreds of Kelvin

Device type `31` selects the RGB UI path used by this integration.

Notifications with marker `4C` or `03` are state events. The app's `resloveState` strips the first 12 hex characters and the last 4 CRC characters, then parses payloads of 8, 12, or 18 hex characters:

- 8 chars: power, scene, brightness, CCT
- 12 chars: power, scene, brightness, CCT, mode, scene
- 18 chars: power, scene, brightness, CCT, hue, saturation, mode, scene, speed/time

The app acknowledges parsed state frames with a `48` response built as:

```text
4C54 <length> <devID> <devType> 48 <state payload> <CRC16>
```

The integration will send the same acknowledgement so the device continues providing state updates.

## 3. Architecture

```text
BT_LED (BLE GATT)
    ↕
GvmBleClient (ble.py)
    - connect / disconnect
    - handshake and device identity
    - CRC frame encode/decode
    - serialized command queue
    - notification parsing and ack
    ↕
GvmDeviceCoordinator (__init__.py)
    - config entry lifecycle
    - reconnect/backoff
    - shared state and entity dispatch
    ↕
GvmLight (light.py)
    - Home Assistant LightEntity
```

The BLE transport has no Home Assistant dependencies beyond `bleak` and logging. It can be unit tested with a fake client. The coordinator and entity use standard Home Assistant patterns.

## 4. Repository layout

```text
custom_components/gvm_800d/
  __init__.py
  ble.py
  config_flow.py
  const.py
  light.py
  manifest.json
  strings.json
  translations/en.json
hacs.json
README.md
LICENSE
tests/
  test_protocol.py
  test_config_flow.py
  test_light.py
```

`manifest.json` will declare domain `gvm_800d`, `config_flow: true`, dependency `bluetooth`, a Bluetooth matcher for service UUID `00010203-0405-0607-0809-0a0b0c0d1910`, and a minimum Home Assistant version of `2024.6.0`. No pip requirement is needed because `bleak` is supplied by Home Assistant's Bluetooth integration.

`hacs.json` will declare an integration-category repository with `render_readme: true`.

## 5. Config flow

- Discovery: Bluetooth advertisements whose name starts with `BT_LED` or whose advertised service UUID matches the GVM service.
- Manual fallback: user enters a MAC address in `AA:BB:CC:DD:EE:FF` form.
- Unique ID: normalized MAC address without separators, uppercase.
- On setup, the integration connects and performs the handshake. Failure aborts with `cannot_connect`; an unexpected device type aborts with `unsupported_device`.
- Re-auth is not needed because the device has no credentials.

## 6. Runtime behavior

### 6.1 Connection sequence

1. Connect to the MAC with `bleak`.
2. Enable notifications on the GVM characteristic.
3. Send the query frame `4C5409000053000001009474`.
4. Parse the handshake response for device ID, device type, and CCT range.
5. For device type `31`, send mode `06 01` once, then again after one second, matching app behavior that forces a known state.
6. Start consuming state notifications.

### 6.2 Command queue

- One async lock serializes all writes.
- A 5-second write timeout and two retries with 200 ms spacing are used.
- Repeated updates for the same command are coalesced so dragging a slider cannot flood the light.
- Frames longer than the app's chunk threshold are split into 20-hex-character writes with 200 ms spacing; the core 24-character frames are written as a single frame with `\r\n`, as the app does.

### 6.3 State updates

- Parsed notifications update the coordinator state immediately.
- A successful write updates HA optimistically; the next notification corrects any mismatch.
- The state acknowledgement frame is queued behind user commands so it cannot reorder them.

## 7. Light entity

The entity supports:

- `is_on` from power byte `01`.
- Brightness 0–255 in HA mapped to device value 0–100.
- HS color: hue 0–360° maps to device 0–75; saturation 0–100% maps to device 0–100 with the observed usable lower bound around 20.
- RGB color is accepted by Home Assistant and converted to HS before being sent.
- Color temperature in Kelvin, clamped to the dynamic min/max from the handshake and sent as Kelvin / 100.
- Setting CCT sends mode `06 01` followed by `03`.
- Setting HS/RGB sends mode `06 02`, then `04` and `05`.
- `available` reflects connection state.

The entity declares `hs`, `rgb`, and `color_temp` as supported color modes. It reports `color_temp` after a CCT command, `hs` after an HS command, and `rgb` after an RGB command. RGB values are converted to device hue/saturation before being sent.

## 8. Error handling

- Initial setup failures raise `ConfigEntryNotReady` for transient BLE errors and abort the flow for unsupported devices.
- Reconnect uses exponential backoff from 5 s to 30 s with jitter.
- After sustained failure, the entity is marked unavailable but the config entry remains configured.
- Queue overflow or repeated write failure logs a warning and drops stale commands rather than blocking newer user input.
- Malformed notifications are ignored and logged at debug level.

## 9. Testing and validation

### 9.1 Unit tests

- CRC16 against all captured frames.
- Command builder for each core command.
- Handshake parser for device ID, type, and CCT bounds.
- State parsers for 8-, 12-, and 18-character payloads.
- HS/RGB conversion and CCT clamping.
- Config flow discovery/manual entry and duplicate handling.
- Light service calls with a fake BLE client.

### 9.2 Live validation

1. Disconnect the phone from `BT_LED` and close the GVM app so HA has exclusive BLE access.
2. Configure the integration in HA with MAC `94:C9:60:B6:CC:87`.
3. Verify handshake, device type, and CCT range are read.
4. Exercise on/off, brightness, CCT, hue, and saturation from HA.
5. Confirm the light responds and notifications update HA state.
6. Confirm reconnect after cycling BLE on the light or restarting the Bluetooth integration.

## 10. Phases after core

### Phase 2 — Effects

Add select entities for mode, scene, and speed using commands `06`, `01`/`07`, and `08`. Validate exact scene mappings against the physical light before exposing them. Do not add microphone-reactive modes.

### Phase 3 — Zones and groups

Check whether zone dimming and multi-device group commands exist on the direct-BLE path. If not, rely on HA-native light groups. Any device-level group support gets a separate spec.

## 11. Success criteria

- The integration installs from a HACS/Marketplace-compatible repository.
- HA discovers or accepts `BT_LED` and creates one light entity.
- Power, brightness, HS/RGB color, and CCT work against the physical GVM 800D RGB.
- Device notifications keep HA state in sync.
- Reconnect recovers from BLE drops without manual reconfiguration.
- Unit tests pass and live validation is recorded in the repository README or a validation note.
