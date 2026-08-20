"""Shared behaviour for forecast sources."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from aiohttp import ClientSession

from ..models import AirportInfo, SourceResult

REQUEST_TIMEOUT = 20
REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": "HomeAssistant/runway_direction",
}


class RunwaySource(ABC):
    """A public page that can be read for runway direction data."""

    name: str
    #: Lower priority numbers win when two sources cover the same period.
    priority: int = 100

    @abstractmethod
    def supports(self, airport: AirportInfo) -> bool:
        """Return whether this source has data for an airport."""

    @abstractmethod
    async def fetch(
        self,
        session: ClientSession,
        airport: AirportInfo,
    ) -> SourceResult:
        """Return the forecast this source holds for an airport."""

    async def _fetch_text(self, session: ClientSession, url: str) -> str:
        """Fetch a page as text."""
        async with asyncio.timeout(REQUEST_TIMEOUT):
            async with session.get(url, headers=REQUEST_HEADERS) as response:
                response.raise_for_status()
                return await response.text()
