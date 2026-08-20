"""The Runway Direction integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import ATTR_ICAO, DOMAIN, SERVICE_REFRESH
from .coordinator import RunwayDirectionCoordinator
from .entity import configured_noise_runways
from .frontend import async_register_card

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

REFRESH_SCHEMA = vol.Schema({vol.Optional(ATTR_ICAO): cv.string})

_LOGGER = logging.getLogger(__name__)


@dataclass
class RunwayDirectionRuntimeData:
    """Runtime data for one configured airport."""

    coordinator: RunwayDirectionCoordinator


RunwayDirectionConfigEntry = ConfigEntry[RunwayDirectionRuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up services and the dashboard card."""
    await async_register_card(hass)

    async def handle_refresh(call: ServiceCall) -> dict[str, Any] | None:
        """Handle the manual refresh action."""
        return await _async_handle_refresh(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH,
        handle_refresh,
        schema=REFRESH_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RunwayDirectionConfigEntry,
) -> bool:
    """Set up one airport from a config entry."""
    coordinator = RunwayDirectionCoordinator(
        hass,
        entry,
        async_get_clientsession(hass),
    )
    await coordinator.async_refresh()

    entry.runtime_data = RunwayDirectionRuntimeData(coordinator=coordinator)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: RunwayDirectionConfigEntry,
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(
    hass: HomeAssistant,
    entry: RunwayDirectionConfigEntry,
) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_handle_refresh(
    hass: HomeAssistant,
    call: ServiceCall,
) -> dict[str, Any] | None:
    """Refresh one airport, or every configured airport."""
    icao = call.data.get(ATTR_ICAO)
    entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if getattr(entry, "runtime_data", None) is not None
        and (icao is None or entry.data.get("icao") == icao)
    ]
    if not entries:
        raise HomeAssistantError(
            f"No loaded Runway Direction entry for {icao}"
            if icao
            else "Runway Direction has no loaded config entry"
        )

    airports: list[dict[str, Any]] = []
    for entry in entries:
        coordinator = entry.runtime_data.coordinator
        try:
            await coordinator.async_request_refresh()
        except Exception as err:  # noqa: BLE001 - action should be automation-friendly
            _LOGGER.debug("Manual refresh failed", exc_info=err)
            raise HomeAssistantError(
                f"Failed to refresh {entry.data.get('icao')}"
            ) from err
        airports.append(_refresh_response(entry))

    if getattr(call, "return_response", False):
        return {"airports": airports}
    return None


def _refresh_response(entry: RunwayDirectionConfigEntry) -> dict[str, Any]:
    """Return a compact summary for automations."""
    data = entry.runtime_data.coordinator.data
    if data is None:
        return {"icao": entry.data.get("icao"), "current_runway": None}

    now = dt_util.now()
    current = data.slot_at(now)
    noise_runways = configured_noise_runways(entry)
    return {
        "icao": data.airport.icao,
        "airport": data.airport.name,
        "current_runway": current.runway if current else None,
        "confidence": current.confidence if current else None,
        "confidence_class": current.confidence_class if current else None,
        "noise_active": current.matches(noise_runways) if current else None,
        "sources": list(data.sources),
    }
