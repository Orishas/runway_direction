"""Register the bundled dashboard card as a frontend resource."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import CARD_FILENAME, CARD_URL_PATH, DATA_CARD_REGISTERED, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_register_card(hass: HomeAssistant) -> None:
    """Serve the bundled card and add it as a Lovelace resource."""
    if hass.data.get(DATA_CARD_REGISTERED):
        return

    card_path = Path(__file__).parent / "www" / CARD_FILENAME
    if not await hass.async_add_executor_job(card_path.is_file):
        _LOGGER.warning("Dashboard card not found at %s", card_path)
        return

    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL_PATH, str(card_path), cache_headers=True)]
        )
    except RuntimeError as err:
        # Raised when the path is already registered, e.g. after a reload.
        _LOGGER.debug("Card path already registered: %s", err)
    else:
        integration = await async_get_integration(hass, DOMAIN)
        add_extra_js_url(hass, f"{CARD_URL_PATH}?v={integration.version}")
        _LOGGER.debug("Registered dashboard card at %s", CARD_URL_PATH)

    hass.data[DATA_CARD_REGISTERED] = True
