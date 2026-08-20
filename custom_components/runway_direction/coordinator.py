"""Coordinator for the Runway Direction integration."""

from __future__ import annotations

import asyncio
from dataclasses import replace
import logging

from aiohttp import ClientSession

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, EVENT_RUNWAY_CHANGED, UPDATE_INTERVAL
from .entity import airport_from_entry, configured_noise_runways
from .merge import merge_results
from .models import RunwayDirectionData, SourceResult
from .sources import SOURCES

_LOGGER = logging.getLogger(__name__)


class RunwayDirectionCoordinator(DataUpdateCoordinator[RunwayDirectionData]):
    """Fetch and merge runway direction data for one airport."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        session: ClientSession,
    ) -> None:
        """Initialize the coordinator."""
        self._airport = airport_from_entry(entry)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {self._airport.icao}",
            update_interval=UPDATE_INTERVAL,
            always_update=False,
        )
        self._session = session
        self._entry = entry

    @property
    def airport(self):
        """Return the configured airport."""
        return self._airport

    async def _async_update_data(self) -> RunwayDirectionData:
        """Fetch every source that covers this airport and merge the results."""
        sources = [source for source in SOURCES if source.supports(self._airport)]
        results: list[SourceResult] = list(
            await asyncio.gather(
                *(source.fetch(self._session, self._airport) for source in sources)
            )
        )

        # The worldwide source also returns the runway layout; keep it fresh.
        for result in results:
            if result.airport is not None and result.airport.runways:
                self._airport = result.airport
                break

        previous = self.data.slot_at(dt_util.now()) if self.data else None
        slots = merge_results(results)
        errors = tuple(
            f"{result.source}: {result.error}" for result in results if result.error
        )

        if not slots:
            raise UpdateFailed("; ".join(errors) or "No usable forecast data")

        data = RunwayDirectionData(
            airport=self._airport,
            slots=slots,
            sources=tuple(result.source for result in results if result.ok),
            errors=errors,
            last_success=dt_util.now().isoformat(),
        )
        self._fire_runway_changed(previous, data)
        return data

    def _fire_runway_changed(
        self,
        previous,
        data: RunwayDirectionData,
    ) -> None:
        """Fire an event when the runway in use changes."""
        current = data.slot_at(dt_util.now())
        if previous is None or current is None:
            return
        if previous.runway == current.runway:
            return

        noise_runways = configured_noise_runways(self._entry)
        self.hass.bus.async_fire(
            EVENT_RUNWAY_CHANGED,
            {
                "icao": data.airport.icao,
                "airport": data.airport.name,
                "old_runway": previous.runway,
                "new_runway": current.runway,
                "confidence": current.confidence,
                "confidence_class": current.confidence_class,
                "noise_runways": list(noise_runways),
                "noise_active": current.matches(noise_runways),
                "source": current.source,
            },
        )
