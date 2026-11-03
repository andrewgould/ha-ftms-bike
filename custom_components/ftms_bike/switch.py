"""The session switch: on connects to the bike, off lets it go."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FtmsConfigEntry
from .entity import FtmsEntity


async def async_setup_entry(hass: HomeAssistant, entry: FtmsConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([SessionSwitch(entry.runtime_data, "session")])


class SessionSwitch(FtmsEntity, SwitchEntity):
    @property
    def available(self) -> bool:
        return self.coordinator.data.in_range or self.coordinator.data.connected

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.connected

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_start_session()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_end_session()
