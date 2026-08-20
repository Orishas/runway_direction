"""Binary sensor platform for the Runway Direction integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import RunwayDirectionConfigEntry
from .const import (
    ATTR_CONFIDENCE,
    ATTR_CONFIDENCE_CLASS,
    ATTR_NEXT_SLOT,
    ATTR_NOISE_RUNWAYS,
    ATTR_RUNWAY,
    ATTR_SOURCE,
    ATTR_STARTS_IN_MINUTES,
    ATTR_WARNING_MINUTES,
    DOMAIN,
)
from .coordinator import RunwayDirectionCoordinator
from .entity import (
    configured_min_confidence,
    configured_noise_runways,
    configured_warning_minutes,
    device_info,
    next_noise_slot,
    starts_in_minutes,
    suggested_object_id,
    without_none,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RunwayDirectionConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Runway Direction binary sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        [
            AircraftNoiseBinarySensor(entry, coordinator),
            AircraftNoiseWarningBinarySensor(entry, coordinator),
            ForecastUncertainBinarySensor(entry, coordinator),
        ]
    )


class BaseBinarySensor(
    CoordinatorEntity[RunwayDirectionCoordinator],
    BinarySensorEntity,
):
    """Shared plumbing for the binary sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: RunwayDirectionConfigEntry,
        coordinator: RunwayDirectionCoordinator,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._entry = entry
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
    def _noise_runways(self) -> tuple[str, ...]:
        return configured_noise_runways(self._entry)

    @property
    def _current(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.slot_at(dt_util.now())


class AircraftNoiseBinarySensor(BaseBinarySensor):
    """Whether the runway in use is one the user considers noisy."""

    def __init__(self, entry, coordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(
            entry,
            coordinator,
            BinarySensorEntityDescription(
                key="aircraft_noise",
                translation_key="aircraft_noise",
                icon="mdi:airplane-alert",
            ),
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self._current is not None

    @property
    def is_on(self) -> bool | None:
        """Return whether a noisy runway is in use."""
        current = self._current
        if current is None:
            return None
        return current.matches(self._noise_runways)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity attributes."""
        current = self._current
        if current is None:
            return {}
        return without_none(
            {
                ATTR_RUNWAY: current.runway,
                ATTR_NOISE_RUNWAYS: list(self._noise_runways),
                ATTR_CONFIDENCE: current.confidence,
                ATTR_CONFIDENCE_CLASS: current.confidence_class,
                ATTR_SOURCE: current.source,
            }
        )


class AircraftNoiseWarningBinarySensor(BaseBinarySensor):
    """Whether a noisy period is forecast within the warning window."""

    def __init__(self, entry, coordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(
            entry,
            coordinator,
            BinarySensorEntityDescription(
                key="aircraft_noise_warning",
                translation_key="aircraft_noise_warning",
                icon="mdi:airplane-clock",
            ),
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether noise starts within the warning window."""
        if self.coordinator.data is None:
            return None
        current = self._current
        if current is not None and current.matches(self._noise_runways):
            return False

        now = dt_util.now()
        slot = next_noise_slot(self.coordinator.data, self._noise_runways, now)
        if slot is None:
            return False
        return starts_in_minutes(slot, now) <= configured_warning_minutes(self._entry)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity attributes."""
        if self.coordinator.data is None:
            return {}
        now = dt_util.now()
        slot = next_noise_slot(self.coordinator.data, self._noise_runways, now)
        return without_none(
            {
                ATTR_WARNING_MINUTES: configured_warning_minutes(self._entry),
                ATTR_STARTS_IN_MINUTES: (
                    starts_in_minutes(slot, now) if slot else None
                ),
                ATTR_NOISE_RUNWAYS: list(self._noise_runways),
                ATTR_NEXT_SLOT: slot.as_dict() if slot else None,
            }
        )


class ForecastUncertainBinarySensor(BaseBinarySensor):
    """Whether the current forecast is below the configured confidence.

    Both sources derive the runway from wind and know nothing about local
    runway usage schemes, so the confidence they report is worth surfacing
    rather than hiding behind a single direction.
    """

    def __init__(self, entry, coordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(
            entry,
            coordinator,
            BinarySensorEntityDescription(
                key="forecast_uncertain",
                translation_key="forecast_uncertain",
                icon="mdi:help-rhombus-outline",
            ),
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the current forecast is uncertain."""
        current = self._current
        if current is None:
            return None
        confidence = current.confidence
        if confidence is None:
            return True
        return confidence < configured_min_confidence(self._entry)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity attributes."""
        current = self._current
        if current is None:
            return {}
        return without_none(
            {
                ATTR_CONFIDENCE: current.confidence,
                ATTR_CONFIDENCE_CLASS: current.confidence_class,
                "min_confidence": configured_min_confidence(self._entry),
                ATTR_SOURCE: current.source,
            }
        )
