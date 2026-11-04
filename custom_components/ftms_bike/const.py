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
# Never send the bike commands: for watching a ride another app is controlling.
CONF_WATCH_ONLY = "watch_only"
# Start a session whenever the bike is heard, instead of waiting for the switch.
CONF_AUTO_SESSION = "auto_session"
# Seconds before an automatic session tries again after a failed connect or a dropped one.
AUTO_RETRY = 60
