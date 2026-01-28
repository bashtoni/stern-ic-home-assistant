"""The Stern Insider Connected integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import SternInsiderConnectedCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Stern Insider Connected from a config entry."""
    # Register frontend card static path (once)
    if DOMAIN not in hass.data:
        www_path = Path(__file__).parent / "www"
        if www_path.exists():
            await hass.http.async_register_static_paths([
                StaticPathConfig(
                    f"/{DOMAIN}",
                    str(www_path),
                    cache_headers=False,
                )
            ])
            _LOGGER.info(
                "Registered Stern Leaderboard card at /%s/stern-leaderboard-card.js",
                DOMAIN
            )

    coordinator = SternInsiderConnectedCoordinator(hass, entry)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store the coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register options update listener
    entry.async_on_unload(entry.add_update_listener(async_options_updated))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    # Reload the integration to apply new options
    await hass.config_entries.async_reload(entry.entry_id)
