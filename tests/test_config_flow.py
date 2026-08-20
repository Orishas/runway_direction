"""Config flow helper tests."""

from __future__ import annotations

import importlib
from pathlib import Path

from custom_components.runway_direction.config_flow import (
    OFFICIAL_ALTERNATIVES,
    _airport_label,
    _distance_key,
    _matches,
    _options_from_input,
)
from custom_components.runway_direction.const import (
    CONF_MIN_CONFIDENCE,
    CONF_NOISE_RUNWAYS,
    CONF_WARNING_MINUTES,
)
from custom_components.runway_direction.sources import rwdf

FIXTURES = Path(__file__).parent / "fixtures"


def _index():
    return rwdf.parse_index((FIXTURES / "rwdf_index.html").read_text(encoding="utf-8"))


def test_search_matches_code_name_and_city() -> None:
    """Any of the obvious search terms finds the airport."""
    airports = {airport.icao: airport for airport in _index()}
    frankfurt = airports["EDDF"]

    for needle in ("eddf", "fra", "frankfurt"):
        assert _matches(frankfurt, needle)
    assert not _matches(frankfurt, "reykjavik")


def test_nearby_airports_sort_by_distance() -> None:
    """With no search term the nearest airports come first."""
    airports = list(_index())
    # Offenbach am Main, next door to Frankfurt.
    ordered = sorted(airports, key=lambda a: _distance_key(a, 50.10, 8.77))

    assert ordered[0].icao == "EDDF"


def test_airport_label_carries_both_codes() -> None:
    """Labels have to disambiguate 2500 airports in a dropdown."""
    airports = {airport.icao: airport for airport in _index()}

    assert "EDDF/FRA" in _airport_label(airports["EDDF"])


def test_frankfurt_points_at_the_official_integration() -> None:
    """Where an official forecast exists, the flow says so."""
    hint = OFFICIAL_ALTERNATIVES["EDDF"]

    assert "fra_betriebsrichtung" in hint
    assert "more accurate" in hint


def test_options_are_normalized() -> None:
    """The form returns strings; the entry stores usable values."""
    options = _options_from_input(
        {
            CONF_NOISE_RUNWAYS: ["25C", "25L"],
            CONF_WARNING_MINUTES: 90.0,
            CONF_MIN_CONFIDENCE: "60",
        }
    )

    assert options == {
        CONF_NOISE_RUNWAYS: ["25C", "25L"],
        CONF_WARNING_MINUTES: 90,
        CONF_MIN_CONFIDENCE: 60,
    }


def test_every_module_imports() -> None:
    """A smoke test: nothing in the integration fails at import time."""
    package = "custom_components.runway_direction"
    modules = [
        path.stem
        for path in Path(package.replace(".", "/")).glob("*.py")
        if path.stem != "__init__"
    ]

    for name in modules:
        importlib.import_module(f"{package}.{name}")

    assert "coordinator" in modules and "diagnostics" in modules
