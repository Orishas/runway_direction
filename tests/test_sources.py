"""Parser tests for both forecast sources, against captured pages."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from custom_components.runway_direction.const import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    SOURCE_BRP,
    SOURCE_RWDF,
)
from custom_components.runway_direction.models import AirportInfo, Runway
from custom_components.runway_direction.sources import brp, rwdf

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(name="frankfurt")
def frankfurt_fixture() -> AirportInfo:
    """Return Frankfurt with its real runway layout."""
    return AirportInfo(
        icao="EDDF",
        slug="frankfurt-am-main-eddf",
        country_slug="germany",
        name="Frankfurt Main Airport",
        iata="FRA",
        runways=(
            Runway("07C/25C", ("07C", "25C"), (69.6, 249.6), 4000),
            Runway("07L/25R", ("07L", "25R"), (69.6, 249.6), 2800),
            Runway("07R/25L", ("07R", "25L"), (69.6, 249.6), 4000),
            Runway("18/36", ("18", "36"), (180.0, 0.0), 4000),
        ),
    )


# --- runwaydirectionforecast.com -------------------------------------------


def test_index_lists_airports_with_addressable_slugs() -> None:
    """The index is the only way to learn an airport's slug."""
    airports = rwdf.parse_index(_fixture("rwdf_index.html"))

    by_icao = {airport.icao: airport for airport in airports}
    assert by_icao["EDDF"].slug == "frankfurt-am-main-eddf"
    assert by_icao["EDDF"].country_slug == "germany"
    assert by_icao["EDDF"].iata == "FRA"
    # Slugs are not derivable from the code — Sydney proves it.
    assert by_icao["YSSY"].slug == "sydney-mascot-yssy"


def test_airport_page_yields_runways_and_forecast(frankfurt: AirportInfo) -> None:
    """An airport page carries the runway layout and a two-day forecast."""
    result = rwdf.parse_airport(_fixture("rwdf_frankfurt.html"), frankfurt)

    assert result.ok
    assert result.source == SOURCE_RWDF
    assert result.airport is not None
    assert {runway.ref for runway in result.airport.runways} == {
        "07C/25C",
        "07L/25R",
        "07R/25L",
        "18/36",
    }
    assert result.airport.runways[0].length_m == 4000

    first = result.slots[0]
    assert first.runway == "25C"
    assert first.runway_ref == "07C/25C"
    assert first.confidence_class == CONFIDENCE_HIGH
    assert first.headwind_kmh == 20
    assert first.crosswind_kmh == 1
    assert first.source == SOURCE_RWDF


def test_airport_page_merges_equal_neighbours(frankfurt: AirportInfo) -> None:
    """Equal, adjacent forecast points become one slot."""
    result = rwdf.parse_airport(_fixture("rwdf_frankfurt.html"), frankfurt)

    assert len(result.slots) < 16
    for previous, current in zip(result.slots, result.slots[1:]):
        assert previous.end == current.start
        assert (previous.runway, previous.confidence_class) != (
            current.runway,
            current.confidence_class,
        )


def test_airport_page_keeps_confidence_verbatim(frankfurt: AirportInfo) -> None:
    """Confidence is carried through unchanged, including where it is wrong.

    The source picks the runway with the best headwind and knows nothing about
    local runway usage. For Frankfurt it proposes runway 18/36 — a
    departure-only runway, with "36" never in use at all — and it does so partly
    at *high* confidence. Confidence therefore filters noise, not nonsense, which
    is why every slot also carries its source and why the docs say plainly that
    this is a wind derivation.
    """
    result = rwdf.parse_airport(_fixture("rwdf_frankfurt.html"), frankfurt)

    classes = {slot.confidence_class for slot in result.slots}
    assert CONFIDENCE_LOW in classes
    assert CONFIDENCE_HIGH in classes

    unusual = [slot for slot in result.slots if slot.runway in {"18", "36"}]
    assert unusual, "the captured page contains the 18/36 proposals"
    assert any(slot.confidence_class == CONFIDENCE_HIGH for slot in unusual)
    assert all(slot.source == SOURCE_RWDF for slot in unusual)


def test_missing_payload_is_an_error_not_a_crash(frankfurt: AirportInfo) -> None:
    """A page without data yields an error result."""
    result = rwdf.parse_airport("<html><body>nothing</body></html>", frankfurt)

    assert not result.ok
    assert result.error


# --- betriebsrichtungsprognose.de ------------------------------------------


def test_brp_picks_the_main_runway_axis(frankfurt: AirportInfo) -> None:
    """Frankfurt's east/west axis wins over the single 18/36 runway."""
    charts = brp.parse_charts(_fixture("brp_frankfurt.html"))
    assert len(charts) == 2

    chart = brp._primary_chart(charts, frankfurt)
    assert chart is not None
    assert {chart["positiveLabel"], chart["negativeLabel"]} == {
        "Ostbetrieb",
        "Westbetrieb",
    }


def test_brp_resolves_axis_to_runway_ends(frankfurt: AirportInfo) -> None:
    """An axis maps onto every runway end pointing that way."""
    result = brp.parse_airport(_fixture("brp_frankfurt.html"), frankfurt)

    assert result.ok
    assert result.source == SOURCE_BRP
    first = result.slots[0]
    assert first.runway is None
    assert set(first.runway_options) == {"25C", "25R", "25L"}
    assert first.direction_text == "west"


def test_brp_never_claims_high_confidence(frankfurt: AirportInfo) -> None:
    """An axis is coarser than a runway, however strong the tendency."""
    result = brp.parse_airport(_fixture("brp_frankfurt.html"), frankfurt)

    assert result.slots
    assert all(
        slot.confidence_class in {CONFIDENCE_MEDIUM, CONFIDENCE_LOW}
        for slot in result.slots
    )


def test_brp_drops_noise_and_calm_wind(frankfurt: AirportInfo) -> None:
    """Weak tendencies and near-calm wind leave gaps instead of guesses."""
    result = brp.parse_airport(_fixture("brp_frankfurt.html"), frankfurt)

    # The official forecast for this window changes direction once.
    changes = sum(
        1
        for previous, current in zip(result.slots, result.slots[1:])
        if previous.direction_text != current.direction_text
    )
    assert changes == 1

    # Dropped points show up as gaps between slots, which is the point.
    assert any(
        previous.end < current.start
        for previous, current in zip(result.slots, result.slots[1:])
    )


def test_brp_single_axis_airport_still_parses() -> None:
    """Munich has one runway axis and one chart."""
    munich = AirportInfo(
        icao="EDDM",
        slug="munich-eddm",
        country_slug="germany",
        name="Munich Airport",
        runways=(
            Runway("08L/26R", ("08L", "26R"), (86.0, 266.0), 4000),
            Runway("08R/26L", ("08R", "26L"), (86.0, 266.0), 4000),
        ),
    )

    result = brp.parse_airport(_fixture("brp_munich.html"), munich)

    assert result.ok
    assert set(result.slots[0].runway_options) <= {"08L", "08R", "26L", "26R"}


def test_brp_covers_only_listed_airports(frankfurt: AirportInfo) -> None:
    """Airports outside Germany and Austria are not supported."""
    source = brp.BrpSource()
    heathrow = AirportInfo(
        icao="EGLL",
        slug="london-egll",
        country_slug="united-kingdom",
        name="Heathrow",
    )

    assert source.supports(frankfurt)
    assert not source.supports(heathrow)


# --- merging ---------------------------------------------------------------


def _slot(source: str, start_h: int, end_h: int, runway: str | None = None) -> object:
    from custom_components.runway_direction.models import RunwaySlot

    base = datetime(2026, 8, 20, tzinfo=timezone.utc)
    return RunwaySlot(
        start=base + timedelta(hours=start_h),
        end=base + timedelta(hours=end_h),
        source=source,
        runway=runway,
    )


def test_merge_lets_the_better_source_win_and_the_other_extend() -> None:
    """The precise source covers its window, the coarse one continues it."""
    from custom_components.runway_direction.merge import merge_results
    from custom_components.runway_direction.models import SourceResult

    precise = SourceResult(SOURCE_RWDF, (_slot(SOURCE_RWDF, 0, 48, "25C"),))
    coarse = SourceResult(SOURCE_BRP, (_slot(SOURCE_BRP, 24, 120),))

    merged = merge_results([precise, coarse])

    assert [(slot.source, slot.start.hour) for slot in merged] == [
        (SOURCE_RWDF, 0),
        (SOURCE_BRP, 0),
    ]
    assert merged[0].end == merged[1].start
    assert merged[1].end.day == 25


def test_merge_keeps_gaps_between_sources() -> None:
    """A gap in the better source is filled by the weaker one."""
    from custom_components.runway_direction.merge import merge_results
    from custom_components.runway_direction.models import SourceResult

    precise = SourceResult(
        SOURCE_RWDF,
        (_slot(SOURCE_RWDF, 0, 6, "25C"), _slot(SOURCE_RWDF, 12, 18, "25C")),
    )
    coarse = SourceResult(SOURCE_BRP, (_slot(SOURCE_BRP, 0, 24),))

    merged = merge_results([precise, coarse])

    assert [(slot.source, slot.start.hour, slot.end.hour) for slot in merged] == [
        (SOURCE_RWDF, 0, 6),
        (SOURCE_BRP, 6, 12),
        (SOURCE_RWDF, 12, 18),
        (SOURCE_BRP, 18, 0),
    ]


def test_merge_ignores_failed_sources() -> None:
    """A source that errored contributes nothing."""
    from custom_components.runway_direction.merge import merge_results
    from custom_components.runway_direction.models import SourceResult

    merged = merge_results(
        [
            SourceResult(SOURCE_RWDF, error="boom"),
            SourceResult(SOURCE_BRP, (_slot(SOURCE_BRP, 0, 6),)),
        ]
    )

    assert len(merged) == 1
    assert merged[0].source == SOURCE_BRP
