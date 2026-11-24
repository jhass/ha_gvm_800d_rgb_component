from custom_components.gvm_800d.ble import (
    build_ack_frame,
    build_command_frame,
    crc16_ccitt,
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
