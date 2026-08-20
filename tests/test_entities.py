"""Entity behaviour tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from custom_components.runway_direction.binary_sensor import (
    AircraftNoiseBinarySensor,
    AircraftNoiseWarningBinarySensor,
    ForecastUncertainBinarySensor,
)
from custom_components.runway_direction.const import (
    CONF_MIN_CONFIDENCE,
    CONF_NOISE_RUNWAYS,
    CONF_WARNING_MINUTES,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_SCORES,
    SOURCE_BRP,
    SOURCE_RWDF,
)
from custom_components.runway_direction.entity import (
    next_noise_slot,
    next_quiet_slot,
    suggested_object_id,
)
from custom_components.runway_direction.models import (
    AirportInfo,
    Runway,
    RunwayDirectionData,
    RunwaySlot,
)
from custom_components.runway_direction.sensor import SENSORS, RunwayDirectionSensor

NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)

AIRPORT = AirportInfo(
    icao="EDDF",
    slug="frankfurt-am-main-eddf",
    country_slug="germany",
    name="Frankfurt Main Airport",
    iata="FRA",
    runways=(Runway("07C/25C", ("07C", "25C"), (69.6, 249.6), 4000),),
)


def _slot(offset_h: int, length_h: int, runway: str | None, **kwargs) -> RunwaySlot:
    return RunwaySlot(
        start=NOW + timedelta(hours=offset_h),
        end=NOW + timedelta(hours=offset_h + length_h),
        source=kwargs.pop("source", SOURCE_RWDF),
        runway=runway,
        confidence_class=kwargs.pop("confidence_class", CONFIDENCE_HIGH),
        **kwargs,
    )


def _data(*slots: RunwaySlot) -> RunwayDirectionData:
    return RunwayDirectionData(
        airport=AIRPORT,
        slots=slots,
        sources=(SOURCE_RWDF,),
    )


def _entry(**options) -> SimpleNamespace:
    return SimpleNamespace(
        data={"icao": "EDDF", "runways": []},
        options={
            CONF_NOISE_RUNWAYS: ["25C"],
            CONF_WARNING_MINUTES: 60,
            CONF_MIN_CONFIDENCE: CONFIDENCE_SCORES[CONFIDENCE_HIGH],
            **options,
        },
    )


def _coordinator(data: RunwayDirectionData | None) -> SimpleNamespace:
    return SimpleNamespace(data=data, airport=AIRPORT)


@pytest.fixture(autouse=True)
def _fixed_now(monkeypatch) -> None:
    """Freeze time for every entity test."""
    for module in (
        "custom_components.runway_direction.sensor",
        "custom_components.runway_direction.binary_sensor",
        "custom_components.runway_direction.entity",
    ):
        monkeypatch.setattr(
            __import__(module, fromlist=["dt_util"]).dt_util,
            "now",
            lambda: NOW,
            raising=False,
        )


def test_object_ids_are_prefixed_per_airport() -> None:
    """Entity ids stay unique and readable across several airports."""
    assert suggested_object_id("EDDF", "forecast") == "eddf_forecast"
    assert suggested_object_id("EGLL", "forecast") == "egll_forecast"


def test_noise_is_on_when_a_selected_runway_is_in_use() -> None:
    """The noise sensor compares the runway in use against the selection."""
    sensor = AircraftNoiseBinarySensor(
        _entry(), _coordinator(_data(_slot(-1, 3, "25C")))
    )
    assert sensor.is_on is True

    sensor = AircraftNoiseBinarySensor(
        _entry(), _coordinator(_data(_slot(-1, 3, "07C")))
    )
    assert sensor.is_on is False


def test_noise_matches_axis_only_slots() -> None:
    """Slots that resolve an axis rather than a runway still match."""
    axis_slot = RunwaySlot(
        start=NOW - timedelta(hours=1),
        end=NOW + timedelta(hours=2),
        source=SOURCE_BRP,
        runway_options=("25C", "25L", "25R"),
        confidence_class=CONFIDENCE_LOW,
    )
    sensor = AircraftNoiseBinarySensor(_entry(), _coordinator(_data(axis_slot)))

    assert sensor.is_on is True


def test_warning_turns_on_inside_the_window_only() -> None:
    """The warning looks ahead exactly as far as configured."""
    data = _data(_slot(-1, 2, "07C"), _slot(1, 3, "25C"))

    inside = AircraftNoiseWarningBinarySensor(
        _entry(**{CONF_WARNING_MINUTES: 90}), _coordinator(data)
    )
    outside = AircraftNoiseWarningBinarySensor(
        _entry(**{CONF_WARNING_MINUTES: 30}), _coordinator(data)
    )

    assert inside.is_on is True
    assert outside.is_on is False


def test_warning_is_off_while_noise_is_already_running() -> None:
    """A warning about noise that already started would be noise, not warning."""
    sensor = AircraftNoiseWarningBinarySensor(
        _entry(), _coordinator(_data(_slot(-1, 3, "25C"), _slot(2, 3, "25C")))
    )
    assert sensor.is_on is False


def test_uncertain_flags_forecasts_below_the_threshold() -> None:
    """Low-confidence periods are surfaced rather than presented as fact."""
    low = ForecastUncertainBinarySensor(
        _entry(), _coordinator(_data(_slot(-1, 3, "25C", confidence_class=CONFIDENCE_LOW)))
    )
    high = ForecastUncertainBinarySensor(
        _entry(), _coordinator(_data(_slot(-1, 3, "25C")))
    )

    assert low.is_on is True
    assert high.is_on is False


def test_next_noise_and_quiet_slots_skip_the_current_one() -> None:
    """Both helpers look forward, not at the period already running."""
    data = _data(_slot(-1, 2, "25C"), _slot(1, 3, "07C"), _slot(4, 3, "25C"))

    noise = next_noise_slot(data, ("25C",), NOW)
    quiet = next_quiet_slot(data, ("25C",), NOW)

    assert noise is not None and noise.start == NOW + timedelta(hours=4)
    assert quiet is not None and quiet.start == NOW + timedelta(hours=1)


def test_current_runway_sensor_reports_runway_and_context() -> None:
    """The main sensor exposes the runway plus where the value came from."""
    description = next(item for item in SENSORS if item.key == "current_runway")
    entity = RunwayDirectionSensor(
        _coordinator(_data(_slot(-1, 3, "25C", headwind_kmh=20, crosswind_kmh=1))),
        description,
    )

    assert entity.native_value == "25C"
    attributes = entity.extra_state_attributes
    assert attributes["confidence"] == CONFIDENCE_SCORES[CONFIDENCE_HIGH]
    assert attributes["source"] == SOURCE_RWDF
    assert attributes["icao"] == "EDDF"


def test_sensors_are_unavailable_without_data() -> None:
    """No forecast means no state, rather than a misleading zero."""
    description = next(item for item in SENSORS if item.key == "current_runway")
    entity = RunwayDirectionSensor(_coordinator(None), description)

    assert entity.native_value is None
