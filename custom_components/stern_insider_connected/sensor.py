"""Sensor platform for Stern Insider Connected."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, HIGH_SCORE_COUNT, HIGH_SCORE_NAMES
from .coordinator import SternInsiderConnectedCoordinator
from .models import Machine


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Stern Insider Connected sensors from a config entry."""
    coordinator: SternInsiderConnectedCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SternHighScoreSensor] = []

    # Create sensors for each machine and each high score rank
    for machine in coordinator.data.values():
        for rank in range(1, HIGH_SCORE_COUNT + 1):
            entities.append(
                SternHighScoreSensor(
                    coordinator=coordinator,
                    machine=machine,
                    rank=rank,
                )
            )

    async_add_entities(entities)


class SternHighScoreSensor(CoordinatorEntity[SternInsiderConnectedCoordinator], SensorEntity):
    """Sensor representing a high score on a pinball machine."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True
    _attr_icon = "mdi:trophy"

    def __init__(
        self,
        coordinator: SternInsiderConnectedCoordinator,
        machine: Machine,
        rank: int,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._machine_id = machine.machine_id
        self._rank = rank
        self._rank_name = HIGH_SCORE_NAMES[rank]

        # Entity identifiers
        self._attr_unique_id = f"{machine.machine_id}_high_score_{rank}"

        # Device info - each machine is a device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, machine.machine_id)},
            name=machine.name,
            manufacturer="Stern Pinball",
            model=machine.game_title,
        )

    @property
    def _machine(self) -> Machine | None:
        """Get the current machine data."""
        if self.coordinator.data:
            return self.coordinator.data.get(self._machine_id)
        return None

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._rank_name

    @property
    def native_value(self) -> int | None:
        """Return the score as the sensor value."""
        machine = self._machine
        if not machine or not machine.high_scores:
            return None

        for score in machine.high_scores:
            if score.rank == self._rank:
                return score.score
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        machine = self._machine
        if not machine:
            return {}

        attrs: dict[str, Any] = {
            "rank": self._rank,
            "machine_name": machine.name,
            "machine_id": machine.machine_id,
            "game_title": machine.game_title,
            "square_logo_url": machine.square_logo_url,
            "variable_width_logo_url": machine.variable_width_logo_url,
            "backglass_image_url": machine.backglass_image_url,
            "background_image_url": machine.background_image_url,
            "gradient_start": machine.gradient_start,
            "gradient_stop": machine.gradient_stop,
        }

        # Find the specific high score for this rank
        for score in machine.high_scores:
            if score.rank == self._rank:
                attrs.update({
                    "player_name": score.player_name,
                    "player_username": score.player_username,
                    "player_initials": score.player_initials,
                    "avatar_url": score.avatar_url,
                })
                break

        return attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
