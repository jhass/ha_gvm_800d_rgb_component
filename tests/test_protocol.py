from custom_components.gvm_800d.ble import (
    build_ack_frame,
    build_command_frame,
    crc16_ccitt,
    parse_handshake,
    parse_state,
)


CAPTURED_FRAMES = [
    "4C5409000053000001009474",
    "4C540900315700060101D5DF",
    "4C540900315700000100775E",
    "4C5409003157000201188A07",
    "4C54090031570005012B09A7",
]


def test_crc_matches_captured_frames():
    for frame in CAPTURED_FRAMES:
        base, crc = frame[:-4], frame[-4:]
        assert f"{crc16_ccitt(bytes.fromhex(base)):04X}" == crc


def test_build_command_frame_matches_capture():
    assert build_command_frame("00", "31", 0x06, 0x01) == "4C540900315700060101D5DF"
    assert build_command_frame("00", "31", 0x00, 0x00) == "4C540900315700000100775E"


def test_build_ack_frame():
    assert build_ack_frame("00", "31", "01020520") == "4C540900314801020520E68F"


def test_parse_handshake():
    frame = "4C54090031530000001E6400020B"
    assert parse_handshake(frame) == {
        "device_id": "00",
        "device_type": "31",
        "cct_min": 3000,
        "cct_max": 10000,
    }


def test_parse_handshake_ignores_default_query():
    assert parse_handshake("4C5409000053000001009474") is None


def test_parse_state_8_char_payload():
    assert parse_state("01020520") == {
        "power": True,
        "scene": 2,
        "brightness": 5,
        "cct_kelvin": 3200,
    }


def test_parse_state_12_char_payload():
    assert parse_state("010205200103")["mode"] == "01"
    assert parse_state("010205200103")["scene_detail"] == 3


def test_parse_state_18_char_payload():
    state = parse_state("010205200A0E01030A")
    assert state["hue"] == 50
    assert state["saturation"] == 14
    assert state["mode"] == "01"
    assert state["scene_detail"] == 3
    assert state["speed_ms"] == 1000


def test_parse_state_rejects_unknown_length():
    assert parse_state("0102") is None
