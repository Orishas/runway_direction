"""Diagnostics for the Runway Direction integration."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import RunwayDirectionConfigEntry
from .sources import SOURCES


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: RunwayDirectionConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a configured airport."""
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data
    airport = coordinator.airport

    return {
        "airport": airport.as_dict(),
        "options": dict(entry.options),
        "sources": {
            source.name: {
                "supported": source.supports(airport),
                "priority": source.priority,
                # Which source actually contributed is visible per slot; a
                # source that silently stops parsing shows up as absent here.
                "slots": (
                    sum(1 for slot in data.slots if slot.source == source.name)
                    if data
                    else 0
                ),
            }
            for source in SOURCES
        },
        "errors": list(data.errors) if data else [],
        "last_success": data.last_success if data else None,
        "slots": [slot.as_dict() for slot in data.slots] if data else [],
    }
