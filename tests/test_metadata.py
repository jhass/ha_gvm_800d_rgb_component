import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_manifest():
    data = json.loads((ROOT / "custom_components/gvm_800d/manifest.json").read_text())
    assert data["domain"] == "gvm_800d"
    assert data["name"] == "GVM 800D RGB"
    assert data["config_flow"] is True
    assert data["dependencies"] == ["bluetooth"]
    assert data["iot_class"] == "local_push"
    matches = [entry["match"] for entry in data["bluetooth"]]
    assert {"service_uuid": "00010203-0405-0607-0809-0a0b0c0d1910"} in matches
    assert {"local_name": "BT_LED"} in matches


def test_hacs_json():
    data = json.loads((ROOT / "hacs.json").read_text())
    assert data["name"] == "GVM 800D RGB"
    assert data["render_readme"] is True
    assert data["homeassistant"] == "2024.6.0"


def test_translations():
    strings = json.loads(
        (ROOT / "custom_components/gvm_800d/strings.json").read_text()
    )
    english = json.loads(
        (ROOT / "custom_components/gvm_800d/translations/en.json").read_text()
    )
    assert strings == english
    assert strings["config"]["step"]["user"]["data"]["device"] == "Discovered light"
    assert strings["config"]["step"]["manual"]["data"]["mac"] == "Bluetooth address"
    assert "invalid_mac" in strings["config"]["error"]
