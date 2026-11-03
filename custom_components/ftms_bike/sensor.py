"""What the bike reports during a session."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfLength,
    UnitOfPower,
    UnitOfSpeed,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FtmsConfigEntry
from .entity import FtmsEntity


@dataclass(frozen=True, kw_only=True)
class FtmsSensorDescription(SensorEntityDescription):
    convert: Callable[[float], float] = lambda v: v


SENSORS = (
    FtmsSensorDescription(
        key="speed", device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1),
    FtmsSensorDescription(
        key="cadence", native_unit_of_measurement="rpm", icon="mdi:rotate-right",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0),
    FtmsSensorDescription(
        key="power", device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT, state_class=SensorStateClass.MEASUREMENT),
    FtmsSensorDescription(
        key="resistance", icon="mdi:speedometer", state_class=SensorStateClass.MEASUREMENT),
    FtmsSensorDescription(
        key="distance", device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS, convert=lambda m: m / 1000,
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2),
    FtmsSensorDescription(
        key="energy", native_unit_of_measurement="kcal", icon="mdi:fire",
        state_class=SensorStateClass.MEASUREMENT),
    FtmsSensorDescription(
        key="elapsed", device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS, state_class=SensorStateClass.MEASUREMENT),
    FtmsSensorDescription(
        key="heart_rate", native_unit_of_measurement="bpm", icon="mdi:heart-pulse",
        state_class=SensorStateClass.MEASUREMENT),
)


async def async_setup_entry(hass: HomeAssistant, entry: FtmsConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities(FtmsSensor(entry.runtime_data, d) for d in SENSORS)


class FtmsSensor(FtmsEntity, SensorEntity):
    entity_description: FtmsSensorDescription

    def __init__(self, coordinator, description: FtmsSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        data = self.coordinator.data
        return data.connected and self.entity_description.key in data.values

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.data.values.get(self.entity_description.key)
        return None if value is None else self.entity_description.convert(value)
