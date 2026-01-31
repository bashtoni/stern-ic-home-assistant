"""The Stern Insider Connected integration."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace import DOMAIN as LOVELACE_DOMAIN
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import SternInsiderConnectedCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

CARD_URL = f"/{DOMAIN}/stern-leaderboard-card.js"


async def _async_register_lovelace_resource(hass: HomeAssistant) -> None:
    """Register the custom card as a Lovelace resource (storage mode only)."""
    # Get the Lovelace resources collection
    lovelace_data = hass.data.get(LOVELACE_DOMAIN)
    if lovelace_data is None:
        _LOGGER.debug("Lovelace not available, skipping resource registration")
        return

    resources: ResourceStorageCollection | None = lovelace_data.get("resources")
    if resources is None:
        _LOGGER.debug("Lovelace not in storage mode, manual resource registration required")
        return

    # Check if resource already registered
    for resource in resources.async_items():
        if resource.get("url", "").startswith(CARD_URL):
            _LOGGER.debug("Stern Leaderboard card resource already registered")
            return

    # Read version from manifest
    manifest_path = Path(__file__).parent / "manifest.json"
    version = "0.0.0"
    if manifest_path.exists():
        with manifest_path.open() as f:
            manifest = json.load(f)
            version = manifest.get("version", version)

    # Register the resource
    resource_url = f"{CARD_URL}?v={version}"
    await resources.async_create_item({"res_type": "module", "url": resource_url})
    _LOGGER.info("Registered Stern Leaderboard card as Lovelace resource: %s", resource_url)


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

            # Auto-register as Lovelace resource (storage mode only)
            await _async_register_lovelace_resource(hass)

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
