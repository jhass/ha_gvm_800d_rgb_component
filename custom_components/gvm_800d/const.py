"""Constants for the GVM 800D RGB integration."""

DOMAIN = "gvm_800d"
CONF_MAC = "mac"
CONF_DEVICE = "device"
ACTION_MANUAL = "manual"
ACTION_RESCAN = "rescan"

SERVICE_UUID = "00010203-0405-0607-0809-0a0b0c0d1910"
CHARACTERISTIC_UUID = "00010203-0405-0607-0809-0a0b0c0d2b10"

HANDSHAKE_FRAME = "4C5409000053000001009474"
COMMAND_PREFIX = "4C5409"
COMMAND_MARKER = "5700"

CMD_POWER = 0x00
CMD_SCENE = 0x01
CMD_BRIGHTNESS = 0x02
CMD_COLOR_TEMP = 0x03
CMD_HUE = 0x04
CMD_SATURATION = 0x05
CMD_MODE = 0x06
CMD_SCENE_SELECT = 0x07
CMD_SPEED = 0x08

MODE_CCT = 0x01
MODE_COLOR = 0x02
MODE_EFFECT = 0x03

PLATFORMS = ["light", "number", "select"]

MODE_CCT_LABEL = "Color temperature"
MODE_COLOR_LABEL = "Color"
MODE_EFFECT_LABEL = "Effect"
MODE_LABELS = {
    MODE_CCT_LABEL: MODE_CCT,
    MODE_COLOR_LABEL: MODE_COLOR,
    MODE_EFFECT_LABEL: MODE_EFFECT,
}

# Scene IDs from the app's rgb31 source list (device type 31).
SCENES = {
    "Lightning": 1,
    "Cop Car": 2,
    "Candle": 3,
    "TV": 4,
    "Bad Bulb": 5,
    "Party": 6,
    "Disco": 7,
    "Paparazzi": 8,
    "Explosion": 9,
    "Pulsing": 10,
    "Flame": 11,
    "Fireworks": 12,
    "Welding": 13,
    "CCT Loop": 14,
    "Hue Loop": 15,
    "Ambulance": 16,
    "Fire Truck": 17,
    "SOS": 18,
}
SCENE_BY_VALUE = {value: label for label, value in SCENES.items()}

SPEED_MIN_MS = 200
SPEED_MAX_MS = 4500
