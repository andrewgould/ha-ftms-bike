"""What the bike reports during a session, and the ride and all-time totals."""

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
    UnitOfEnergy,
    UnitOfLength,
    UnitOfPower,
    UnitOfSpeed,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FtmsConfigEntry
from .entity import FtmsEntity
from .tally import Tally


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



@dataclass(frozen=True, kw_only=True)
class TallySensorDescription(SensorEntityDescription):
    value: Callable[[Tally], float | None]


def _average_power(tally: Tally) -> float | None:
    ride = tally.ride
    return round(ride["work"] / ride["elapsed"]) if ride["elapsed"] else None


# Totals count every session for good, so Home Assistant's statistics can show them
# per day, week or month like a smart plug's energy. The ride ones restart with each
# session and keep the last ride's figures until the next.
TALLIES = (
    TallySensorDescription(
        key="total_distance", device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        value=lambda t: t.total["distance"] / 1000),
    TallySensorDescription(
        key="total_work", device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_JOULE,
        state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=0,
        value=lambda t: t.total["work"] / 1000),
    TallySensorDescription(
        key="total_calories", native_unit_of_measurement="kcal", icon="mdi:fire",
        state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=0,
        value=lambda t: t.total["energy"]),
    TallySensorDescription(
        key="total_time", device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        value=lambda t: t.total["elapsed"]),
    TallySensorDescription(
        key="ride_distance", device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS, suggested_display_precision=2,
        value=lambda t: t.ride["distance"] / 1000),
    TallySensorDescription(
        key="ride_work", device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_JOULE, suggested_display_precision=0,
        value=lambda t: t.ride["work"] / 1000),
    TallySensorDescription(
        key="ride_calories", native_unit_of_measurement="kcal", icon="mdi:fire",
        suggested_display_precision=0, value=lambda t: t.ride["energy"]),
    TallySensorDescription(
        key="ride_time", device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.MINUTES, suggested_display_precision=0,
        value=lambda t: t.ride["elapsed"]),
    TallySensorDescription(
        key="ride_average_power", device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT, value=_average_power),
)


async def async_setup_entry(hass: HomeAssistant, entry: FtmsConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities([*(FtmsSensor(coordinator, d) for d in SENSORS),
                        *(TallySensor(coordinator, d) for d in TALLIES)])


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


class TallySensor(FtmsEntity, SensorEntity):
    """Available whenever the integration is loaded, session or not."""

    entity_description: TallySensorDescription

    def __init__(self, coordinator, description: TallySensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value(self.coordinator.tally)
