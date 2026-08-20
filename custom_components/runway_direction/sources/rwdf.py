"""runwaydirectionforecast.com — worldwide coverage.

The site renders every page from one JSON blob in ``window.flightForecastData``.
The overview page carries the full airport index, an airport page carries that
airport's runways plus a two-day forecast in three-hour steps.

The forecast is derived from wind: it picks the runway with the best headwind.
It does not know local runway usage schemes, noise abatement rules or capacity
constraints, so its confidence class matters and is carried through unchanged.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import re
from typing import Any

from aiohttp import ClientSession

from ..const import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    RWDF_BASE_URL,
    RWDF_LANGUAGE,
    SOURCE_RWDF,
)
from ..models import AirportInfo, Runway, RunwaySlot, SourceResult
from .base import RunwaySource

_PAYLOAD_RE = re.compile(r"window\.flightForecastData\s*=\s*(\{.*?\})\s*;", re.S)

_CONFIDENCE_CLASSES = {
    "high": CONFIDENCE_HIGH,
    "medium": CONFIDENCE_MEDIUM,
    "low": CONFIDENCE_LOW,
}

# The last forecast entry has no successor to bound it.
_TRAILING_SLOT_HOURS = 3


def airport_page_url(airport: AirportInfo) -> str:
    """Return the page URL for an airport."""
    return f"{RWDF_BASE_URL}/{RWDF_LANGUAGE}/{airport.country_slug}/{airport.slug}/"


def parse_payload(html: str) -> dict[str, Any] | None:
    """Return the page's data blob."""
    match = _PAYLOAD_RE.search(html)
    if match is None:
        return None
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def parse_index(html: str) -> tuple[AirportInfo, ...]:
    """Return every airport the site knows about.

    Slugs cannot be derived from a name or code (``YSSY`` is
    ``sydney-mascot-yssy``), so the index is the only way to address an
    airport. It is read once during config flow, never while polling.
    """
    payload = parse_payload(html)
    if payload is None:
        return ()

    airports: list[AirportInfo] = []
    for entry in payload.get("airports", []):
        if not isinstance(entry, dict):
            continue
        icao = entry.get("icao")
        slug = entry.get("slug")
        country_slug = entry.get("country_slug")
        if not icao or not slug or not country_slug:
            continue
        airports.append(
            AirportInfo(
                icao=str(icao),
                slug=str(slug),
                country_slug=str(country_slug),
                name=str(entry.get("name") or icao),
                iata=_optional_str(entry.get("iata")),
                city=_optional_str(entry.get("city")),
                lat=_optional_float(entry.get("lat")),
                lon=_optional_float(entry.get("lon")),
            )
        )
    return tuple(airports)


def parse_airport(html: str, airport: AirportInfo) -> SourceResult:
    """Return the forecast and runway layout from an airport page."""
    payload = parse_payload(html)
    if payload is None:
        return SourceResult(source=SOURCE_RWDF, error="No data on page")

    resolved = _merge_airport(airport, payload.get("airport"))
    slots = _parse_slots(payload.get("forecast"))
    if not slots:
        return SourceResult(
            source=SOURCE_RWDF,
            airport=resolved,
            error="No forecast entries",
        )
    return SourceResult(source=SOURCE_RWDF, airport=resolved, slots=slots)


def _merge_airport(airport: AirportInfo, raw: Any) -> AirportInfo:
    """Fill in runway layout and identity details from the page."""
    if not isinstance(raw, dict):
        return airport

    runways: list[Runway] = []
    for entry in raw.get("runways", []):
        if not isinstance(entry, dict) or entry.get("closed"):
            continue
        ends = tuple(
            str(entry[key]) for key in ("a", "b") if _optional_str(entry.get(key))
        )
        if not ends:
            continue
        headings = tuple(
            heading
            for heading in (
                _optional_float(entry.get("a_heading")),
                _optional_float(entry.get("b_heading")),
            )
            if heading is not None
        )
        length_ft = _optional_float(entry.get("length_ft"))
        runways.append(
            Runway(
                ref=str(entry.get("ref") or "/".join(ends)),
                ends=ends,
                headings=headings,
                length_m=round(length_ft * 0.3048) if length_ft else None,
            )
        )

    return replace(
        airport,
        name=str(raw.get("name") or airport.name),
        iata=_optional_str(raw.get("iata")) or airport.iata,
        city=_optional_str(raw.get("city")) or airport.city,
        lat=_optional_float(raw.get("lat")) or airport.lat,
        lon=_optional_float(raw.get("lon")) or airport.lon,
        runways=tuple(runways),
    )


def _parse_slots(raw: Any) -> tuple[RunwaySlot, ...]:
    """Turn forecast entries into slots, merging equal neighbours."""
    if not isinstance(raw, list):
        return ()

    entries = [entry for entry in raw if isinstance(entry, dict)]
    slots: list[RunwaySlot] = []
    for index, entry in enumerate(entries):
        start = _timestamp(entry.get("timestamp"))
        if start is None:
            continue
        end = (
            _timestamp(entries[index + 1].get("timestamp"))
            if index + 1 < len(entries)
            else None
        )
        if end is None:
            end = start + timedelta(hours=_TRAILING_SLOT_HOURS)
        if end <= start:
            continue

        runway = _optional_str(entry.get("runway"))
        slot = RunwaySlot(
            start=start,
            end=end,
            source=SOURCE_RWDF,
            runway=runway,
            runway_ref=_optional_str(entry.get("runway_ref")),
            heading=_optional_int(entry.get("runway_heading")),
            direction_text=_optional_str(entry.get("takeoff_to_text")),
            confidence_class=_CONFIDENCE_CLASSES.get(
                str(entry.get("confidence_class", "")).lower()
            ),
            wind_kmh=_optional_int(entry.get("wind_kmh")),
            gust_kmh=_optional_int(entry.get("wind_gust_kmh")),
            headwind_kmh=_optional_int(entry.get("headwind_kmh")),
            crosswind_kmh=_optional_int(entry.get("crosswind_kmh")),
        )

        previous = slots[-1] if slots else None
        if (
            previous is not None
            and previous.runway == slot.runway
            and previous.confidence_class == slot.confidence_class
            and previous.end == slot.start
        ):
            slots[-1] = replace(previous, end=slot.end)
            continue
        slots.append(slot)
    return tuple(slots)


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value, timezone.utc)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    number = _optional_float(value)
    return round(number) if number is not None else None


class RwdfSource(RunwaySource):
    """Worldwide runway forecast."""

    name = SOURCE_RWDF
    priority = 1

    def supports(self, airport: AirportInfo) -> bool:
        """Every configured airport comes from this source's index."""
        return bool(airport.slug and airport.country_slug)

    async def fetch(
        self,
        session: ClientSession,
        airport: AirportInfo,
    ) -> SourceResult:
        """Return the forecast for an airport."""
        try:
            html = await self._fetch_text(session, airport_page_url(airport))
        except Exception as err:  # noqa: BLE001 - network failures are recoverable
            return SourceResult(source=SOURCE_RWDF, error=str(err))
        return parse_airport(html, airport)
