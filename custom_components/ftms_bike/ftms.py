"""Bluetooth Fitness Machine Service (FTMS) for indoor bikes: decoding and commands.

No Home Assistant imports, so the tests can load it on its own.
"""

from __future__ import annotations

import math
import struct

FTMS_SERVICE = "00001826-0000-1000-8000-00805f9b34fb"
FEATURE = "00002acc-0000-1000-8000-00805f9b34fb"
INDOOR_BIKE_DATA = "00002ad2-0000-1000-8000-00805f9b34fb"
RESISTANCE_RANGE = "00002ad6-0000-1000-8000-00805f9b34fb"
POWER_RANGE = "00002ad8-0000-1000-8000-00805f9b34fb"
CONTROL_POINT = "00002ad9-0000-1000-8000-00805f9b34fb"

# Control point op codes.
OP_REQUEST_CONTROL = 0x00
OP_SET_RESISTANCE = 0x04
OP_SET_POWER = 0x05
OP_RESPONSE = 0x80

RESULTS = {
    0x01: "success",
    0x02: "not supported",
    0x03: "invalid parameter",
    0x04: "operation failed",
    0x05: "control not permitted",
}
RESULT_SUCCESS = 0x01
RESULT_NOT_PERMITTED = 0x05

# Machine type bit in the FTMS advertisement's service data.
TYPE_INDOOR_BIKE = 1 << 5


class FtmsError(Exception):
    """The bike refused a command."""


def is_indoor_bike(service_data: bytes | None) -> bool:
    """True unless the advertisement says it's some other kind of machine.

    Service data is flags (1 byte) then machine type (2 bytes). Consoles that leave
    it out get the benefit of the doubt.
    """
    if not service_data or len(service_data) < 3:
        return True
    return bool(int.from_bytes(service_data[1:3], "little") & TYPE_INDOOR_BIKE)


def parse_indoor_bike_data(data: bytes) -> dict[str, float | int]:
    """Decode one Indoor Bike Data notification into the fields it carries.

    Consoles split a reading over several notifications ("more data" set on all but
    the last), so a frame only has some of the fields; merge them as they come.
    """
    flags = int.from_bytes(data[0:2], "little")
    pos = 2
    out: dict[str, float | int] = {}

    def take(fmt: str) -> int:
        nonlocal pos
        (value,) = struct.unpack_from(fmt, data, pos)
        pos += struct.calcsize(fmt)
        return value

    if not flags & 0x0001:  # bit 0 is "more data": speed is present when it's clear
        out["speed"] = take("<H") / 100
    if flags & 0x0002:
        take("<H")  # average speed
    if flags & 0x0004:
        out["cadence"] = take("<H") / 2
    if flags & 0x0008:
        take("<H")  # average cadence
    if flags & 0x0010:
        out["distance"] = int.from_bytes(data[pos:pos + 3], "little")
        pos += 3
    if flags & 0x0020:
        out["resistance"] = take("<h")
    if flags & 0x0040:
        out["power"] = take("<h")
    if flags & 0x0080:
        take("<h")  # average power
    if flags & 0x0100:
        out["energy"] = take("<H")
        take("<H")  # per hour
        take("<B")  # per minute
    if flags & 0x0200:
        heart_rate = take("<B")
        if heart_rate:  # 0 means nothing is sending heart rate to the console
            out["heart_rate"] = heart_rate
    if flags & 0x0400:
        take("<B")  # metabolic equivalent
    if flags & 0x0800:
        out["elapsed"] = take("<H")
    if flags & 0x1000:
        take("<H")  # remaining time
    return out


def parse_range(data: bytes, fmt: str = "<hhH") -> tuple[int, int, int]:
    """A supported-range characteristic: minimum, maximum, increment."""
    return struct.unpack_from(fmt, data, 0)


def request_control() -> bytes:
    return bytes([OP_REQUEST_CONTROL])


# How a console reads Set Target Resistance.
SCALE_TENTHS = "tenths"  # as the standard says: tenths of a level
SCALE_SPREAD = "spread"  # one byte, 0-255 spread across all the levels


def default_scale(supported: tuple[int, int, int]) -> str:
    """A guess for consoles nobody has set: a byte of tenths can't reach past level 25.5,
    so a console with more levels than that probably spreads the byte instead."""
    return SCALE_SPREAD if supported[1] > 255 else SCALE_TENTHS


def resistance_raw(level: float, supported: tuple[int, int, int], scale: str) -> int:
    """The Set Target Resistance value for a console level.

    The SM-810's console has two Bluetooth modules that disagree. FS-92D16A spreads
    0-255 across its 32 levels (raw 100 is level 12, 255 is 32) and keeps only the
    low byte of anything bigger, so 320 lands on level 8. Its twin reads tenths, so
    raw 80 is level 8.
    """
    low, high, _ = supported
    if scale == SCALE_SPREAD:
        return max(low, min(255, math.ceil(level * 255 / (high / 10))))
    return max(low, min(high, round(level * 10)))


def set_resistance(raw: int) -> bytes:
    """One byte, as the standard has it, unless the value needs two."""
    if raw <= 255:
        return bytes([OP_SET_RESISTANCE, raw])
    return bytes([OP_SET_RESISTANCE]) + struct.pack("<h", raw)


def set_power(watts: int) -> bytes:
    return bytes([OP_SET_POWER]) + struct.pack("<h", watts)


def parse_response(data: bytes) -> tuple[int, int] | None:
    """A control point indication: (request op code, result code), or None if it isn't one."""
    if len(data) < 3 or data[0] != OP_RESPONSE:
        return None
    return data[1], data[2]
