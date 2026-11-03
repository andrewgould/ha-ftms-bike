"""Constants for the FTMS indoor bike integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "ftms_bike"
PLATFORMS = [Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]

# A session ends by itself after this long without pedalling, so a forgotten
# session can't keep the bike from Kinomap or Zwift.
IDLE_TIMEOUT = 300
# Seconds to wait for the bike to answer a command.
COMMAND_TIMEOUT = 5
# Supported Resistance Level Range (tenths of a level) to assume if the bike doesn't say.
DEFAULT_RESISTANCE_RANGE = (10, 320, 10)

CONF_RESISTANCE_SCALE = "resistance_scale"
