"""Config flow for the Runway Direction integration."""

from __future__ import annotations

from math import cos, radians
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_AIRPORT_NAME,
    CONF_COUNTRY_SLUG,
    CONF_ICAO,
    CONF_MIN_CONFIDENCE,
    CONF_NOISE_RUNWAYS,
    CONF_SLUG,
    CONF_WARNING_MINUTES,
    CONFIDENCE_SCORES,
    DEFAULT_MIN_CONFIDENCE,
    DEFAULT_WARNING_MINUTES,
    DOMAIN,
    MAX_WARNING_MINUTES,
    MIN_WARNING_MINUTES,
    RWDF_INDEX_URL,
    WARNING_MINUTES_STEP,
)
from .models import AirportInfo
from .sources import rwdf
from .sources.base import REQUEST_HEADERS, REQUEST_TIMEOUT

CONF_SEARCH = "search"
CONF_AIRPORT = "airport"

# Airports that have a dedicated integration fed by an official forecast,
# which is more accurate than any wind derivation can be.
OFFICIAL_ALTERNATIVES = {
    "EDDF": (
        " For Frankfurt there is a dedicated integration using the official "
        "Umwelthaus forecast, which is more accurate: "
        "https://github.com/Orishas/fra_betriebsrichtung"
    ),
}

MAX_RESULTS = 25


def _distance_key(airport: AirportInfo, lat: float, lon: float) -> float:
    """Return a cheap squared distance for sorting nearby airports."""
    if airport.lat is None or airport.lon is None:
        return float("inf")
    scale = cos(radians(lat)) or 1.0
    return (airport.lat - lat) ** 2 + ((airport.lon - lon) * scale) ** 2


def _matches(airport: AirportInfo, needle: str) -> bool:
    """Return whether an airport matches a search term."""
    haystack = " ".join(
        part.lower()
        for part in (airport.icao, airport.iata, airport.name, airport.city)
        if part
    )
    return needle in haystack


def _confidence_options() -> list[SelectOptionDict]:
    return [
        SelectOptionDict(value=str(score), label=name)
        for name, score in CONFIDENCE_SCORES.items()
    ]


def _settings_schema(
    runway_ends: tuple[str, ...],
    noise_runways: tuple[str, ...] = (),
    warning_minutes: int = DEFAULT_WARNING_MINUTES,
    min_confidence: int = DEFAULT_MIN_CONFIDENCE,
) -> vol.Schema:
    """Return the schema for noise runways and thresholds."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_NOISE_RUNWAYS,
                default=list(noise_runways),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=list(runway_ends),
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                )
            ),
            vol.Required(
                CONF_WARNING_MINUTES,
                default=warning_minutes,
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_WARNING_MINUTES,
                    max=MAX_WARNING_MINUTES,
                    step=WARNING_MINUTES_STEP,
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_MIN_CONFIDENCE,
                default=str(min_confidence),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=_confidence_options(),
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


class RunwayDirectionConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Runway Direction."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._airports: tuple[AirportInfo, ...] = ()
        self._matches: tuple[AirportInfo, ...] = ()
        self._airport: AirportInfo | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: Any) -> RunwayDirectionOptionsFlow:
        """Create the options flow."""
        return RunwayDirectionOptionsFlow()

    async def _async_index(self) -> tuple[AirportInfo, ...]:
        """Fetch the airport index once per flow.

        Slugs are not derivable from a code, so the index is the only way to
        address an airport. It is read here and never while polling.
        """
        if self._airports:
            return self._airports
        session = async_get_clientsession(self.hass)
        async with session.get(
            RWDF_INDEX_URL,
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT,
        ) as response:
            response.raise_for_status()
            html = await response.text()
        self._airports = rwdf.parse_index(html)
        return self._airports

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Search for an airport."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                airports = await self._async_index()
            except Exception:  # noqa: BLE001 - surfaced as a form error
                errors["base"] = "cannot_connect"
            else:
                needle = str(user_input.get(CONF_SEARCH, "")).strip().lower()
                if needle:
                    found = [a for a in airports if _matches(a, needle)]
                else:
                    found = sorted(
                        airports,
                        key=lambda airport: _distance_key(
                            airport,
                            self.hass.config.latitude,
                            self.hass.config.longitude,
                        ),
                    )
                if not found:
                    errors["base"] = "no_airports"
                else:
                    self._matches = tuple(found[:MAX_RESULTS])
                    return await self.async_step_select()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Optional(CONF_SEARCH): TextSelector()}),
            errors=errors,
        )

    async def async_step_select(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Pick one airport from the search results."""
        if user_input is not None:
            icao = user_input[CONF_AIRPORT]
            await self.async_set_unique_id(icao)
            self._abort_if_unique_id_configured()

            airport = next(a for a in self._matches if a.icao == icao)
            session = async_get_clientsession(self.hass)
            try:
                async with session.get(
                    rwdf.airport_page_url(airport),
                    headers=REQUEST_HEADERS,
                    timeout=REQUEST_TIMEOUT,
                ) as response:
                    response.raise_for_status()
                    html = await response.text()
            except Exception:  # noqa: BLE001 - surfaced as a form error
                return self.async_show_form(
                    step_id="select",
                    data_schema=self._select_schema(),
                    errors={"base": "cannot_connect"},
                )

            result = rwdf.parse_airport(html, airport)
            self._airport = result.airport or airport
            return await self.async_step_settings()

        return self.async_show_form(step_id="select", data_schema=self._select_schema())

    def _select_schema(self) -> vol.Schema:
        options = [
            SelectOptionDict(
                value=airport.icao,
                label=_airport_label(airport),
            )
            for airport in self._matches
        ]
        return vol.Schema(
            {
                vol.Required(CONF_AIRPORT): SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )

    async def async_step_settings(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Choose which runway ends are noisy, and the thresholds."""
        assert self._airport is not None
        airport = self._airport

        if user_input is not None:
            return self.async_create_entry(
                title=_airport_label(airport),
                data={
                    CONF_ICAO: airport.icao,
                    CONF_SLUG: airport.slug,
                    CONF_COUNTRY_SLUG: airport.country_slug,
                    CONF_AIRPORT_NAME: airport.name,
                    "iata": airport.iata,
                    "city": airport.city,
                    "runways": [
                        {
                            "ref": runway.ref,
                            "ends": list(runway.ends),
                            "headings": list(runway.headings),
                            "length_m": runway.length_m,
                        }
                        for runway in airport.runways
                    ],
                },
                options=_options_from_input(user_input),
            )

        return self.async_show_form(
            step_id="settings",
            data_schema=_settings_schema(airport.runway_ends),
            description_placeholders={
                "airport": _airport_label(airport),
                "official": OFFICIAL_ALTERNATIVES.get(airport.icao, ""),
            },
        )


class RunwayDirectionOptionsFlow(OptionsFlow):
    """Handle options for a configured airport."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=_options_from_input(user_input))

        runway_ends: list[str] = []
        for runway in self.config_entry.data.get("runways", []):
            for end in runway.get("ends", []):
                if end not in runway_ends:
                    runway_ends.append(end)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=_settings_schema(
                tuple(runway_ends),
                tuple(options.get(CONF_NOISE_RUNWAYS, ())),
                options.get(CONF_WARNING_MINUTES, DEFAULT_WARNING_MINUTES),
                options.get(CONF_MIN_CONFIDENCE, DEFAULT_MIN_CONFIDENCE),
            ),
        )


def _options_from_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Normalize the settings form into stored options."""
    return {
        CONF_NOISE_RUNWAYS: list(user_input.get(CONF_NOISE_RUNWAYS, [])),
        CONF_WARNING_MINUTES: int(user_input[CONF_WARNING_MINUTES]),
        CONF_MIN_CONFIDENCE: int(user_input[CONF_MIN_CONFIDENCE]),
    }


def _airport_label(airport: AirportInfo) -> str:
    """Return a human-readable airport label."""
    codes = airport.icao if not airport.iata else f"{airport.icao}/{airport.iata}"
    if airport.city and airport.city.lower() not in airport.name.lower():
        return f"{airport.name}, {airport.city} ({codes})"
    return f"{airport.name} ({codes})"
