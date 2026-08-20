"""Data models for the Runway Direction integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .const import CONFIDENCE_SCORES


@dataclass(frozen=True)
class Runway:
    """A physical runway with its two ends."""

    ref: str
    ends: tuple[str, ...] = ()
    headings: tuple[float, ...] = ()
    length_m: int | None = None
    closed: bool = False

    def as_dict(self) -> dict[str, Any]:
        """Return the Home Assistant attribute representation."""
        return {
            "ref": self.ref,
            "ends": list(self.ends),
            "length_m": self.length_m,
            "closed": self.closed,
        }


@dataclass(frozen=True)
class AirportInfo:
    """Identity and layout of a configured airport."""

    icao: str
    slug: str
    country_slug: str
    name: str
    iata: str | None = None
    city: str | None = None
    lat: float | None = None
    lon: float | None = None
    runways: tuple[Runway, ...] = ()

    @property
    def runway_ends(self) -> tuple[str, ...]:
        """Return every selectable runway end, in a stable order."""
        ends: list[str] = []
        for runway in self.runways:
            for end in runway.ends:
                if end not in ends:
                    ends.append(end)
        return tuple(ends)

    def as_dict(self) -> dict[str, Any]:
        """Return the Home Assistant attribute representation."""
        return {
            "icao": self.icao,
            "iata": self.iata,
            "name": self.name,
            "city": self.city,
            "runways": [runway.as_dict() for runway in self.runways],
        }


@dataclass(frozen=True)
class RunwaySlot:
    """A forecast period with the runway expected to be in use."""

    start: datetime
    end: datetime
    source: str
    runway: str | None = None
    # Sources that only resolve an axis (east/west) rather than a single
    # runway list every end that fits, instead of picking one arbitrarily.
    runway_options: tuple[str, ...] = ()
    runway_ref: str | None = None
    heading: int | None = None
    direction_text: str | None = None
    confidence_class: str | None = None
    wind_kmh: int | None = None
    gust_kmh: int | None = None
    headwind_kmh: int | None = None
    crosswind_kmh: int | None = None

    @property
    def confidence(self) -> int | None:
        """Return the confidence as a comparable number."""
        if self.confidence_class is None:
            return None
        return CONFIDENCE_SCORES.get(self.confidence_class)

    def matches(self, runways: tuple[str, ...] | list[str]) -> bool:
        """Return whether this slot uses one of the given runway ends."""
        if self.runway is not None:
            return self.runway in runways
        return any(end in runways for end in self.runway_options)

    def as_dict(self) -> dict[str, Any]:
        """Return the Home Assistant attribute representation."""
        values: dict[str, Any] = {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "from": self.start.strftime("%H:%M"),
            "to": self.end.strftime("%H:%M"),
            "date": self.start.date().isoformat(),
            "source": self.source,
        }
        for key, value in (
            ("runway", self.runway),
            ("runway_options", list(self.runway_options) or None),
            ("runway_ref", self.runway_ref),
            ("heading", self.heading),
            ("direction", self.direction_text),
            ("confidence", self.confidence),
            ("confidence_class", self.confidence_class),
            ("wind_kmh", self.wind_kmh),
            ("gust_kmh", self.gust_kmh),
            ("headwind_kmh", self.headwind_kmh),
            ("crosswind_kmh", self.crosswind_kmh),
        ):
            if value is not None:
                values[key] = value
        return values


@dataclass(frozen=True)
class SourceResult:
    """What a single source returned for one update."""

    source: str
    slots: tuple[RunwaySlot, ...] = ()
    airport: AirportInfo | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        """Return whether the source delivered usable data."""
        return self.error is None and bool(self.slots)


@dataclass(frozen=True)
class RunwayDirectionData:
    """Normalized forecast for one airport."""

    airport: AirportInfo
    slots: tuple[RunwaySlot, ...] = ()
    sources: tuple[str, ...] = ()
    errors: tuple[str, ...] = field(default=(), compare=False)
    last_success: str | None = field(default=None, compare=False)

    @property
    def has_forecast(self) -> bool:
        """Return whether any forecast slot is available."""
        return bool(self.slots)

    def slot_at(self, moment: datetime) -> RunwaySlot | None:
        """Return the slot covering a point in time."""
        return next(
            (slot for slot in self.slots if slot.start <= moment < slot.end),
            None,
        )

    def next_slot_after(self, moment: datetime) -> RunwaySlot | None:
        """Return the first slot starting after a point in time."""
        return next((slot for slot in self.slots if slot.start > moment), None)
