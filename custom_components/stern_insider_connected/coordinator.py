"""Data update coordinator for Stern Insider Connected."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    SternAPIError,
    SternAuthenticationError,
    SternConnectionError,
    SternInsiderConnectedAPI,
)
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_NEW_HIGH_SCORE,
)
from .models import HighScore, Machine

_LOGGER = logging.getLogger(__name__)


class SternInsiderConnectedCoordinator(DataUpdateCoordinator[dict[str, Machine]]):
    """Coordinator for fetching Stern Insider Connected data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the coordinator."""
        self.entry = entry
        self._api: SternInsiderConnectedAPI | None = None
        self._previous_scores: dict[str, dict[int, str]] = {}  # machine_id -> {rank: score_id}

        # Get scan interval from options or use default
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=scan_interval),
        )

    @property
    def api(self) -> SternInsiderConnectedAPI:
        """Get the API client, creating it if necessary."""
        if self._api is None:
            session = async_get_clientsession(self.hass)
            self._api = SternInsiderConnectedAPI(
                username=self.entry.data[CONF_USERNAME],
                password=self.entry.data[CONF_PASSWORD],
                session=session,
            )
        return self._api

    async def _async_update_data(self) -> dict[str, Machine]:
        """Fetch data from the Stern API."""
        try:
            machines = await self.api.get_machines()

            # Fetch high scores for each machine
            result: dict[str, Machine] = {}
            for machine in machines:
                try:
                    high_scores = await self.api.get_high_scores(machine.machine_id)
                    machine.high_scores = high_scores
                    result[machine.machine_id] = machine

                    # Check for new high scores and fire events
                    self._check_new_scores(machine, high_scores)
                except SternAPIError as err:
                    _LOGGER.warning(
                        "Failed to fetch high scores for %s: %s",
                        machine.name,
                        err,
                    )
                    result[machine.machine_id] = machine

            return result

        except SternAuthenticationError as err:
            raise ConfigEntryAuthFailed(
                "Authentication failed - please re-authenticate"
            ) from err
        except SternConnectionError as err:
            raise UpdateFailed(f"Failed to connect to Stern API: {err}") from err
        except SternAPIError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

    def _check_new_scores(self, machine: Machine, high_scores: list[HighScore]) -> None:
        """Check for new high scores and fire events."""
        machine_id = machine.machine_id
        previous = self._previous_scores.get(machine_id, {})
        current: dict[int, str] = {}

        for score in high_scores:
            current[score.rank] = score.score_id

            # Check if this is a new score
            previous_score_id = previous.get(score.rank)
            is_new_entry = previous_score_id is not None and previous_score_id != score.score_id

            if is_new_entry:
                _LOGGER.info(
                    "New high score detected: %s scored %d on %s (rank %d)",
                    score.player_name,
                    score.score,
                    machine.name,
                    score.rank,
                )
                self._fire_new_score_event(machine, score, is_new_entry=True)

        # Update stored scores for next comparison
        self._previous_scores[machine_id] = current

    def _fire_new_score_event(
        self, machine: Machine, score: HighScore, is_new_entry: bool
    ) -> None:
        """Fire an event for a new high score."""
        event_data: dict[str, Any] = {
            "machine_id": machine.machine_id,
            "machine_name": machine.name,
            "score": score.score,
            "rank": score.rank,
            "player_name": score.player_name,
            "player_username": score.player_username,
            "player_initials": score.player_initials,
            "is_new_entry": is_new_entry,
        }

        self.hass.bus.async_fire(EVENT_NEW_HIGH_SCORE, event_data)
