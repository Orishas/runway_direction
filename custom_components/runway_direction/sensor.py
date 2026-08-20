"""Sensor platform for the Runway Direction integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import RunwayDirectionConfigEntry
from .const import (
    ATTR_AIRPORT,
    ATTR_CONFIDENCE,
    ATTR_CONFIDENCE_CLASS,
    ATTR_CROSSWIND_KMH,
    ATTR_HEADING,
    ATTR_HEADWIND_KMH,
    ATTR_IATA,
    ATTR_ICAO,
    ATTR_NEXT_SLOT,
    ATTR_NOISE_RUNWAYS,
    ATTR_RUNWAY_REF,
    ATTR_SLOTS,
    ATTR_SOURCE,
    ATTR_SOURCES,
    ATTR_WIND_KMH,
    DOMAIN,
)
from .coordinator import RunwayDirectionCoordinator
from .entity import (
    configured_noise_runways,
    device_info,
    next_noise_slot,
    suggested_object_id,
    without_none,
)
from .models import RunwayDirectionData, RunwaySlot


@dataclass(frozen=True, kw_only=True)
class RunwaySensorEntityDescription(SensorEntityDescription):
    """Describes a Runway Direction sensor."""

    value_fn: Callable[[RunwayDirectionData, RunwaySlot | None], Any]
    attrs_fn: Callable[[RunwayDirectionData, RunwaySlot | None], dict[str, Any]]


def _current_value(data: RunwayDirectionData, current: RunwaySlot | None) -> Any:
    if current is None:
        return None
    return current.runway or current.direction_text


def _current_attrs(
    data: RunwayDirectionData,
    current: RunwaySlot | None,
) -> dict[str, Any]:
    if current is None:
        return {}
    return without_none(
        {
            ATTR_RUNWAY_REF: current.runway_ref,
            ATTR_HEADING: current.heading,
            ATTR_CONFIDENCE: current.confidence,
            ATTR_CONFIDENCE_CLASS: current.confidence_class,
            ATTR_WIND_KMH: current.wind_kmh,
            ATTR_HEADWIND_KMH: current.headwind_kmh,
            ATTR_CROSSWIND_KMH: current.crosswind_kmh,
            ATTR_SOURCE: current.source,
            ATTR_AIRPORT: data.airport.name,
            ATTR_ICAO: data.airport.icao,
            ATTR_IATA: data.airport.iata,
        }
    )


def _forecast_value(data: RunwayDirectionData, current: RunwaySlot | None) -> Any:
    upcoming = data.next_slot_after(dt_util.now())
    if upcoming is None:
        return None
    return upcoming.runway or upcoming.direction_text


def _forecast_attrs(
    data: RunwayDirectionData,
    current: RunwaySlot | None,
) -> dict[str, Any]:
    upcoming = data.next_slot_after(dt_util.now())
    return without_none(
        {
            ATTR_NEXT_SLOT: upcoming.as_dict() if upcoming else None,
            ATTR_SLOTS: [slot.as_dict() for slot in data.slots],
            ATTR_SOURCES: list(data.sources),
            ATTR_AIRPORT: data.airport.name,
            ATTR_ICAO: data.airport.icao,
        }
    )


def _confidence_value(data: RunwayDirectionData, current: RunwaySlot | None) -> Any:
    return current.confidence if current else None


def _confidence_attrs(
    data: RunwayDirectionData,
    current: RunwaySlot | None,
) -> dict[str, Any]:
    if current is None:
        return {}
    return without_none(
        {
            ATTR_CONFIDENCE_CLASS: current.confidence_class,
            ATTR_SOURCE: current.source,
        }
    )


def _wind_attrs(
    data: RunwayDirectionData,
    current: RunwaySlot | None,
) -> dict[str, Any]:
    if current is None:
        return {}
    return without_none({ATTR_SOURCE: current.source})


SENSORS: tuple[RunwaySensorEntityDescription, ...] = (
    RunwaySensorEntityDescription(
        key="current_runway",
        translation_key="current_runway",
        icon="mdi:airport",
        value_fn=_current_value,
        attrs_fn=_current_attrs,
    ),
    RunwaySensorEntityDescription(
        key="forecast",
        translation_key="forecast",
        icon="mdi:calendar-clock",
        value_fn=_forecast_value,
        attrs_fn=_forecast_attrs,
    ),
    RunwaySensorEntityDescription(
        key="confidence",
        translation_key="confidence",
        icon="mdi:progress-question",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_confidence_value,
        attrs_fn=_confidence_attrs,
    ),
    RunwaySensorEntityDescription(
        key="headwind",
        translation_key="headwind",
        icon="mdi:weather-windy",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement="km/h",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, current: current.headwind_kmh if current else None,
        attrs_fn=_wind_attrs,
    ),
    RunwaySensorEntityDescription(
        key="crosswind",
        translation_key="crosswind",
        icon="mdi:weather-windy-variant",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement="km/h",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, current: current.crosswind_kmh if current else None,
        attrs_fn=_wind_attrs,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RunwayDirectionConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Runway Direction sensors."""
    coordinator = entry.runtime_data.coordinator
    entities: list[SensorEntity] = [
        RunwayDirectionSensor(coordinator, description) for description in SENSORS
    ]
    entities.append(NextAircraftNoiseSensor(entry, coordinator))
    async_add_entities(entities)


class RunwayDirectionSensor(
    CoordinatorEntity[RunwayDirectionCoordinator],
    SensorEntity,
):
    """A sensor derived from the merged forecast."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RunwayDirectionCoordinator,
        description: RunwaySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        icao = coordinator.airport.icao
        self._attr_unique_id = f"{DOMAIN}_{icao}_{description.key}"
        self._attr_device_info = device_info(coordinator.airport)

    @property
    def suggested_object_id(self) -> str:
        """Return a stable, language-independent entity object id."""
        return suggested_object_id(
            self.coordinator.airport.icao,
            self.entity_description.key,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self.native_value is not None

    @property
    def _current(self) -> RunwaySlot | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.slot_at(dt_util.now())

    @property
    def native_value(self) -> Any:
        """Return the sensor state."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data, self._current)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity attributes."""
        if self.coordinator.data is None:
            return {}
        return self.entity_description.attrs_fn(self.coordinator.data, self._current)


class NextAircraftNoiseSensor(
    CoordinatorEntity[RunwayDirectionCoordinator],
    SensorEntity,
):
    """When the next forecast period uses one of the noisy runway ends."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    entity_description = SensorEntityDescription(
        key="next_aircraft_noise",
        translation_key="next_aircraft_noise",
        icon="mdi:calendar-alert",
    )

    def __init__(
        self,
        entry: RunwayDirectionConfigEntry,
        coordinator: RunwayDirectionCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        icao = coordinator.airport.icao
        self._attr_unique_id = f"{DOMAIN}_{icao}_next_aircraft_noise"
        self._attr_device_info = device_info(coordinator.airport)

    @property
    def suggested_object_id(self) -> str:
        """Return a stable, language-independent entity object id."""
        return suggested_object_id(
            self.coordinator.airport.icao,
            "next_aircraft_noise",
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self.native_value is not None

    @property
    def _slot(self) -> RunwaySlot | None:
        return next_noise_slot(
            self.coordinator.data,
            configured_noise_runways(self._entry),
            dt_util.now(),
        )

    @property
    def native_value(self) -> datetime | None:
        """Return the start of the next noisy period."""
        slot = self._slot
        return slot.start if slot else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity attributes."""
        slot = self._slot
        if slot is None:
            return {}
        return without_none(
            {
                **slot.as_dict(),
                ATTR_NOISE_RUNWAYS: list(configured_noise_runways(self._entry)),
            }
        )
