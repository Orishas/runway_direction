"""betriebsrichtungsprognose.de — Germany and Austria, five days.

This source reaches three days further than the worldwide one, but is coarser:
it resolves an axis (east/west, north/south) rather than a single runway, and
publishes a tendency from -100 to 100 derived from wind.

It is therefore used only to extend a forecast, never to replace one, and its
slots never claim high confidence.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
import json
import re
from typing import Any

from aiohttp import ClientSession

from ..const import (
    BRP_BASE_URL,
    BRP_MIN_TENDENCY,
    BRP_MIN_WIND_KN,
    BRP_SLOT_HOURS,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    SOURCE_BRP,
)
from ..models import AirportInfo, RunwaySlot, SourceResult
from .base import RunwaySource

_CHART_RE = re.compile(r"window\.BRP_CHARTS\.push\(\s*(\{.*?\})\s*\)\s*;", re.S)
_LABEL_RE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\s+(\d{2}):(\d{2})$")

# Airports this source covers, keyed by ICAO. Rostock-Laage (ETNL) and
# Schwerin-Parchim (EDOP) are covered by the site but absent from the
# worldwide index, so they can never be configured and are left out.
BRP_SLUGS = {
    "EDDB": "berlin-schoenefeld-sxf-ber",
    "EDDW": "bremen-bre",
    "EDLW": "dortmund-dtm",
    "EDDC": "dresden-drs",
    "EDDL": "duesseldorf-dus",
    "EDDE": "erfurt-weimar-erf",
    "EDDF": "frankfurt-fra",
    "EDFH": "frankfurt-hahn-hhn",
    "EDNY": "friedrichshafen-fdh",
    "LOWG": "graz-grz",
    "EDDH": "hamburg-ham",
    "EDDV": "hannover-haj",
    "LOWI": "innsbruck-inn",
    "EDSB": "karlsruhe-baden-baden-fkb",
    "EDVK": "kassel-ksf",
    "LOWK": "klagenfurt-klu",
    "EDDK": "koeln-bonn-cgn",
    "EDDP": "leipzig-halle-lej",
    "LOWL": "linz-lnz",
    "EDDM": "muenchen-muc",
    "EDDG": "muenster-osnabrueck-fmo",
    "EDDN": "nuernberg-nue",
    "EDLP": "paderborn-lippstadt-pad",
    "LFSB": "basel-muelhausen-freiburg-eap-bsl-mlh",
    "LOWS": "salzburg-szg",
    "EDDS": "stuttgart-str",
    "LOWW": "wien-vie",
}

# Chart labels mapped onto a compass sector of runway headings.
_AXIS_SECTORS = {
    "ostbetrieb": ("east", 45.0, 135.0),
    "suedbetrieb": ("south", 135.0, 225.0),
    "südbetrieb": ("south", 135.0, 225.0),
    "westbetrieb": ("west", 225.0, 315.0),
    "nordbetrieb": ("north", 315.0, 45.0),
}


def airport_page_url(icao: str) -> str:
    """Return the page URL for an airport."""
    return f"{BRP_BASE_URL}/{BRP_SLUGS[icao]}/"


def parse_charts(html: str) -> tuple[dict[str, Any], ...]:
    """Return every chart config on the page."""
    charts: list[dict[str, Any]] = []
    for match in _CHART_RE.finditer(html):
        try:
            chart = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(chart, dict):
            charts.append(chart)
    return tuple(charts)


def parse_airport(html: str, airport: AirportInfo) -> SourceResult:
    """Return the forecast from an airport page."""
    charts = parse_charts(html)
    if not charts:
        return SourceResult(source=SOURCE_BRP, error="No chart data on page")

    chart = _primary_chart(charts, airport)
    if chart is None:
        return SourceResult(source=SOURCE_BRP, error="No axis matches the runways")

    slots = _parse_slots(chart, airport)
    if not slots:
        return SourceResult(source=SOURCE_BRP, error="No usable forecast points")
    return SourceResult(source=SOURCE_BRP, slots=slots)


def _primary_chart(
    charts: tuple[dict[str, Any], ...],
    airport: AirportInfo,
) -> dict[str, Any] | None:
    """Return the chart describing the airport's main runway axis.

    Airports with two runway systems get one chart each. The axis serving the
    most runway ends is the main one — for Frankfurt that is east/west with
    three runways, not north/south with the single runway 18/36.
    """
    best: tuple[int, dict[str, Any]] | None = None
    for chart in charts:
        matched = 0
        for label in (chart.get("positiveLabel"), chart.get("negativeLabel")):
            sector = _AXIS_SECTORS.get(str(label or "").strip().lower())
            if sector is not None:
                matched += len(_ends_in_sector(airport, sector))
        if matched and (best is None or matched > best[0]):
            best = (matched, chart)
    return best[1] if best else None


def _ends_in_sector(
    airport: AirportInfo,
    sector: tuple[str, float, float],
) -> tuple[str, ...]:
    """Return runway ends whose heading falls inside a compass sector."""
    _, low, high = sector
    ends: list[str] = []
    for runway in airport.runways:
        for end, heading in zip(runway.ends, runway.headings):
            inside = low <= heading < high if low < high else (heading >= low or heading < high)
            if inside:
                ends.append(end)
    return tuple(ends)


def _parse_slots(
    chart: dict[str, Any],
    airport: AirportInfo,
) -> tuple[RunwaySlot, ...]:
    """Build merged slots from a chart config."""
    labels = chart.get("labels")
    values = chart.get("direction")
    if not isinstance(labels, list) or not isinstance(values, list):
        return ()
    winds = chart.get("wind") if isinstance(chart.get("wind"), list) else []

    positive = _AXIS_SECTORS.get(str(chart.get("positiveLabel", "")).strip().lower())
    negative = _AXIS_SECTORS.get(str(chart.get("negativeLabel", "")).strip().lower())
    if positive is None or negative is None:
        return ()

    slots: list[RunwaySlot] = []
    count = min(len(labels), len(values))
    for index in range(count):
        start = _label_datetime(labels[index])
        if start is None:
            continue
        end = (
            _label_datetime(labels[index + 1])
            if index + 1 < count
            else start + timedelta(hours=BRP_SLOT_HOURS)
        )
        if end is None or end <= start:
            continue

        wind = winds[index] if index < len(winds) else None
        resolved = _resolve(values[index], wind)
        if resolved is None:
            # Below either threshold the source cannot support a direction.
            # Leave a gap rather than publishing a guess.
            continue
        tendency, confidence = resolved
        sector = positive if tendency > 0 else negative

        slot = RunwaySlot(
            start=start,
            end=end,
            source=SOURCE_BRP,
            runway_options=_ends_in_sector(airport, sector),
            direction_text=sector[0],
            confidence_class=confidence,
            wind_kmh=_knots_to_kmh(wind),
        )

        previous = slots[-1] if slots else None
        if (
            previous is not None
            and previous.direction_text == slot.direction_text
            and previous.confidence_class == slot.confidence_class
            and previous.end == slot.start
        ):
            slots[-1] = replace(previous, end=slot.end)
            continue
        slots.append(slot)
    return tuple(slots)


def _resolve(value: Any, wind: Any) -> tuple[float, str] | None:
    """Return (tendency, confidence class), or None when not meaningful."""
    try:
        tendency = float(value)
    except (TypeError, ValueError):
        return None
    if abs(tendency) < BRP_MIN_TENDENCY:
        return None
    try:
        if wind is not None and float(wind) < BRP_MIN_WIND_KN:
            return None
    except (TypeError, ValueError):
        pass
    # Never "high": an axis is coarser than a runway, whatever the tendency.
    return tendency, CONFIDENCE_MEDIUM if abs(tendency) >= 80 else CONFIDENCE_LOW


def _label_datetime(label: Any) -> datetime | None:
    """Parse a chart label such as 'Thu 20.08 12:11' into a local datetime."""
    if not isinstance(label, str):
        return None
    match = _LABEL_RE.search(label.strip())
    if match is None:
        return None

    day, month, hour, minute = (int(part) for part in match.groups())
    now = datetime.now().astimezone()
    try:
        parsed = datetime(
            now.year, month, day, hour, minute, tzinfo=now.tzinfo
        )
    except ValueError:
        return None

    if parsed < now - timedelta(days=180):
        return parsed.replace(year=parsed.year + 1)
    if parsed > now + timedelta(days=180):
        return parsed.replace(year=parsed.year - 1)
    return parsed


def _knots_to_kmh(value: Any) -> int | None:
    try:
        return round(float(value) * 1.852)
    except (TypeError, ValueError):
        return None


class BrpSource(RunwaySource):
    """Five-day forecast for German and Austrian airports."""

    name = SOURCE_BRP
    priority = 2

    def supports(self, airport: AirportInfo) -> bool:
        """Return whether this source covers an airport."""
        return airport.icao in BRP_SLUGS

    async def fetch(
        self,
        session: ClientSession,
        airport: AirportInfo,
    ) -> SourceResult:
        """Return the forecast for an airport."""
        try:
            html = await self._fetch_text(session, airport_page_url(airport.icao))
        except Exception as err:  # noqa: BLE001 - network failures are recoverable
            return SourceResult(source=SOURCE_BRP, error=str(err))
        return parse_airport(html, airport)
