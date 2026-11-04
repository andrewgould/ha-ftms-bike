"""Resistance and target power, settable during a session."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEFAULT_RESISTANCE_RANGE, DOMAIN
from .coordinator import FtmsConfigEntry
from .entity import FtmsEntity

# Supported Resistance Level Range is in tenths of a level.
RESISTANCE_SCALE = 10
# Power range to offer before the bike has said what it supports.
DEFAULT_POWER = (10, 1000, 10)
# Bikes claim absurd maximums (9,999 W); nobody needs the slider to go that far.
POWER_CAP = 1000


async def async_setup_entry(hass: HomeAssistant, entry: FtmsConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    keys = ("target_resistance", "target_power")
    if coordinator.watch_only:
        # Nothing to set, so don't leave the targets lying around unavailable.
        registry = er.async_get(hass)
        for key in keys:
            if entity_id := registry.async_get_entity_id(
                    "number", DOMAIN, f"{coordinator.address}_{key}"):
                registry.async_remove(entity_id)
        return
    async_add_entities([ResistanceNumber(coordinator, keys[0]),
                        PowerNumber(coordinator, keys[1])])


class _SessionNumber(FtmsEntity, NumberEntity):
    @property
    def available(self) -> bool:
        return self.coordinator.data.connected


class ResistanceNumber(_SessionNumber):
    _attr_icon = "mdi:speedometer"
    _attr_mode = NumberMode.SLIDER

    def _range(self) -> tuple[int, int, int]:
        return self.coordinator.data.resistance_range or DEFAULT_RESISTANCE_RANGE

    @property
    def native_min_value(self) -> float:
        return self._range()[0] / RESISTANCE_SCALE

    @property
    def native_max_value(self) -> float:
        return self._range()[1] / RESISTANCE_SCALE

    @property
    def native_step(self) -> float:
        return max(self._range()[2], 1) / RESISTANCE_SCALE

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if data.target_resistance is not None:
            return data.target_resistance
        return data.values.get("resistance")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_resistance(value)


class PowerNumber(_SessionNumber):
    _attr_device_class = NumberDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_mode = NumberMode.BOX

    def _range(self) -> tuple[int, int, int]:
        return self.coordinator.data.power_range or DEFAULT_POWER

    @property
    def native_min_value(self) -> float:
        return self._range()[0]

    @property
    def native_max_value(self) -> float:
        return min(self._range()[1], POWER_CAP)

    @property
    def native_step(self) -> float:
        return max(self._range()[2], 1)

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.target_power

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_power(int(value))
