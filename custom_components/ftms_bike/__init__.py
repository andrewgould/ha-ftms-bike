"""An indoor bike's Bluetooth FTMS console, connected only for sessions someone starts."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .coordinator import FtmsConfigEntry, FtmsCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: FtmsConfigEntry) -> bool:
    coordinator = FtmsCoordinator(hass, entry)
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_start()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FtmsConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    await entry.runtime_data.async_stop()
    return unloaded
