"""Decoding and command tests for the FTMS module, using frames from a Lifespan SM-810."""

import importlib.util
import pathlib

_path = pathlib.Path(__file__).parents[1] / "custom_components/ftms_bike/ftms.py"
_spec = importlib.util.spec_from_file_location("ftms", _path)
ftms = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ftms)


def test_full_reading():
    frame = bytes.fromhex("540b72055800d40f003e003e00000000006003")
    assert ftms.parse_indoor_bike_data(frame) == {
        "speed": 13.94, "cadence": 44.0, "distance": 4052, "power": 62,
        "energy": 62, "elapsed": 864,
    }


def test_resistance_only_frame_has_no_speed():
    # "More data" is set, so the speed field is absent and the resistance comes first.
    assert ftms.parse_indoor_bike_data(bytes.fromhex("21000100")) == {"resistance": 1}


def test_zero_heart_rate_is_left_out():
    frame = bytes.fromhex("540b72055800d40f003e003e00000000006003")
    assert "heart_rate" not in ftms.parse_indoor_bike_data(frame)
    with_hr = bytearray(frame)
    with_hr[16] = 128
    assert ftms.parse_indoor_bike_data(bytes(with_hr))["heart_rate"] == 128


def test_ranges():
    assert ftms.parse_range(bytes.fromhex("0a0040010a00")) == (10, 320, 10)
    assert ftms.parse_range(bytes.fromhex("0a000f270a00")) == (10, 9999, 10)


def test_commands():
    assert ftms.request_control() == b"\x00"
    assert ftms.set_resistance(50) == b"\x04\x32"
    assert ftms.set_power(150) == b"\x05\x96\x00"


def test_responses():
    assert ftms.parse_response(bytes.fromhex("800401")) == (0x04, ftms.RESULT_SUCCESS)
    assert ftms.parse_response(bytes.fromhex("800005")) == (0x00, ftms.RESULT_NOT_PERMITTED)
    assert ftms.parse_response(bytes.fromhex("0401")) is None


def test_machine_type_from_service_data():
    assert ftms.is_indoor_bike(bytes([0x01, 0x20, 0x00]))
    assert not ftms.is_indoor_bike(bytes([0x01, 0x01, 0x00]))  # treadmill
    assert ftms.is_indoor_bike(None)


def test_resistance_on_a_32_level_console():
    # Measured on the SM-810, which reports a range of 10-320: level = raw * 32 // 255.
    sm810 = (10, 320, 10)
    measured = {10: 1, 50: 6, 100: 12, 200: 25, 248: 31, 255: 32}
    for raw, level in measured.items():
        assert raw * 32 // 255 == level
    for level in range(1, 33):
        raw = ftms.resistance_raw(level, sm810, ftms.SCALE_SPREAD)
        assert 10 <= raw <= 255
        assert raw * 32 // 255 == level


def test_resistance_on_a_standard_console():
    tenths = ftms.SCALE_TENTHS
    assert ftms.resistance_raw(5, (10, 200, 10), tenths) == 50
    assert ftms.resistance_raw(30, (10, 200, 10), tenths) == 200
    assert ftms.resistance_raw(0, (10, 200, 10), tenths) == 10
    # The SM-810's twin module: level 10 needs raw 100, where spread would send 80 (level 8).
    assert ftms.resistance_raw(10, (10, 320, 10), tenths) == 100
    assert ftms.resistance_raw(10, (10, 320, 10), ftms.SCALE_SPREAD) == 80
    assert ftms.set_resistance(300) == b"\x04\x2c\x01"


def test_default_scale():
    assert ftms.default_scale((10, 320, 10)) == ftms.SCALE_SPREAD
    assert ftms.default_scale((10, 200, 10)) == ftms.SCALE_TENTHS
