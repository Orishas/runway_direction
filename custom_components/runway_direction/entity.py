"""Shared entity helpers for the Runway Direction integration."""

from __future__ import annotations

from datetime import datetime
from math import ceil
from typing import Any

from homeassistant.util import dt as dt_util

from .const import (
    CONF_AIRPORT_NAME,
    CONF_COUNTRY_SLUG,
    CONF_ICAO,
    CONF_MIN_CONFIDENCE,
    CONF_NOISE_RUNWAYS,
    CONF_SLUG,
    CONF_WARNING_MINUTES,
    DEFAULT_MIN_CONFIDENCE,
    DEFAULT_WARNING_MINUTES,
    DOMAIN,
    RWDF_BASE_URL,
)
from .models import AirportInfo, Runway, RunwayDirectionData, RunwaySlot


def airport_from_entry(entry: Any) -> AirportInfo:
    """Rebuild the configured airport from a config entry."""
    data = entry.data
    return AirportInfo(
        icao=data[CONF_ICAO],
        slug=data[CONF_SLUG],
        country_slug=data[CONF_COUNTRY_SLUG],
        name=data.get(CONF_AIRPORT_NAME) or data[CONF_ICAO],
        iata=data.get("iata"),
        city=data.get("city"),
        runways=tuple(
            Runway(
                ref=runway["ref"],
                ends=tuple(runway.get("ends", ())),
                headings=tuple(runway.get("headings", ())),
                length_m=runway.get("length_m"),
            )
            for runway in data.get("runways", [])
        ),
    )


def configured_noise_runways(entry: Any) -> tuple[str, ...]:
    """Return the runway ends the user considers noisy."""
    return tuple(entry.options.get(CONF_NOISE_RUNWAYS, ()))


def configured_warning_minutes(entry: Any) -> int:
    """Return the warning window in minutes."""
    return int(entry.options.get(CONF_WARNING_MINUTES, DEFAULT_WARNING_MINUTES))


def configured_min_confidence(entry: Any) -> int:
    """Return the confidence below which a forecast counts as uncertain."""
    return int(entry.options.get(CONF_MIN_CONFIDENCE, DEFAULT_MIN_CONFIDENCE))


def device_info(airport: AirportInfo) -> dict[str, Any]:
    """Return device info for one airport."""
    return {
        "configuration_url": (
            f"{RWDF_BASE_URL}/en/{airport.country_slug}/{airport.slug}/"
        ),
        "identifiers": {(DOMAIN, airport.icao)},
        "manufacturer": "Runway Direction",
        "model": airport.icao,
        "name": airport.name,
    }


def suggested_object_id(icao: str, key: str) -> str:
    """Return a stable, language-independent entity object id."""
    return f"{icao.lower()}_{key}"


def next_noise_slot(
    data: RunwayDirectionData | None,
    noise_runways: tuple[str, ...],
    now: datetime | None = None,
) -> RunwaySlot | None:
    """Return the next slot using one of the noisy runway ends."""
    if data is None or not noise_runways:
        return None
    moment = now or dt_util.now()
    active = data.slot_at(moment)
    for slot in data.slots:
        if slot.end <= moment:
            continue
        if not slot.matches(noise_runways):
            continue
        if active is not None and slot is active:
            continue
        return slot
    return None


def next_quiet_slot(
    data: RunwayDirectionData | None,
    noise_runways: tuple[str, ...],
    now: datetime | None = None,
) -> RunwaySlot | None:
    """Return the next slot that does not use a noisy runway end."""
    if data is None:
        return None
    moment = now or dt_util.now()
    for slot in data.slots:
        if slot.end <= moment:
            continue
        if slot.matches(noise_runways):
            continue
        return slot
    return None


def starts_in_minutes(slot: RunwaySlot, now: datetime) -> int:
    """Return minutes until a slot starts."""
    return ceil((slot.start - now).total_seconds() / 60)


def without_none(values: dict[str, Any]) -> dict[str, Any]:
    """Return a copy without None values."""
    return {key: value for key, value in values.items() if value is not None}
