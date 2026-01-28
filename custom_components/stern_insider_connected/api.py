"""API client for Stern Insider Connected."""

from __future__ import annotations

import logging
import time
from typing import Any

import aiohttp

from .const import (
    API_HIGH_SCORES_URL,
    API_LOGIN_URL,
    API_MACHINES_URL,
    API_TEAMS_URL,
    TOKEN_EXPIRY_BUFFER,
)
from .models import HighScore, Machine, Team, TeamMember

_LOGGER = logging.getLogger(__name__)


class SternAPIError(Exception):
    """Base exception for Stern API errors."""


class SternAuthenticationError(SternAPIError):
    """Authentication failed."""


class SternConnectionError(SternAPIError):
    """Connection to API failed."""


class SternInsiderConnectedAPI:
    """API client for Stern Insider Connected."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialise the API client."""
        self._username = username
        self._password = password
        self._session = session
        self._owns_session = session is None
        self._access_token: str | None = None
        self._token_expiry: float = 0

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure we have a valid session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        """Close the session if we own it."""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()

    def _is_token_valid(self) -> bool:
        """Check if the current token is valid."""
        if not self._access_token:
            return False
        return time.time() < (self._token_expiry - TOKEN_EXPIRY_BUFFER)

    async def authenticate(self) -> bool:
        """Authenticate with the Stern API."""
        session = await self._ensure_session()

        try:
            async with session.post(
                API_LOGIN_URL,
                json={"username": self._username, "password": self._password},
            ) as response:
                if response.status == 401:
                    raise SternAuthenticationError("Invalid username or password")
                if response.status == 403:
                    raise SternAuthenticationError("Account access denied")
                if response.status != 200:
                    raise SternAPIError(
                        f"Authentication failed with status {response.status}"
                    )

                data = await response.json()
                self._access_token = data.get("accessToken") or data.get("access_token")
                if not self._access_token:
                    raise SternAPIError("No access token in response")

                # Token typically expires in 30 minutes
                expires_in = data.get("expiresIn", data.get("expires_in", 1800))
                self._token_expiry = time.time() + expires_in

                _LOGGER.debug("Successfully authenticated with Stern API")
                return True

        except aiohttp.ClientError as err:
            raise SternConnectionError(f"Failed to connect to Stern API: {err}") from err

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid authentication token."""
        if not self._is_token_valid():
            await self.authenticate()

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an authenticated request to the API."""
        await self._ensure_authenticated()
        session = await self._ensure_session()

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._access_token}"

        try:
            async with session.request(method, url, headers=headers, **kwargs) as response:
                if response.status in (401, 403):
                    # Token may have expired, try re-authenticating once
                    self._access_token = None
                    await self._ensure_authenticated()
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    async with session.request(
                        method, url, headers=headers, **kwargs
                    ) as retry_response:
                        if retry_response.status in (401, 403):
                            raise SternAuthenticationError(
                                "Authentication failed after retry"
                            )
                        retry_response.raise_for_status()
                        return await retry_response.json()

                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientError as err:
            raise SternConnectionError(f"API request failed: {err}") from err

    async def get_machines(self) -> list[Machine]:
        """Get all machines for the authenticated user."""
        data = await self._request("GET", API_MACHINES_URL)

        machines = []
        for item in data.get("machines", data if isinstance(data, list) else []):
            machine = Machine(
                machine_id=str(item.get("id", item.get("machineId", ""))),
                name=item.get("name", item.get("machineName", "Unknown")),
                game_title=item.get("gameTitle", item.get("game_title", "Unknown")),
                image_url=item.get("imageUrl", item.get("image_url")),
            )
            machines.append(machine)

        return machines

    async def get_high_scores(self, machine_id: str) -> list[HighScore]:
        """Get high scores for a specific machine."""
        url = API_HIGH_SCORES_URL.format(machine_id=machine_id)
        data = await self._request("GET", url)

        high_scores = []
        scores_list = data.get("highScores", data.get("scores", data if isinstance(data, list) else []))

        for item in scores_list:
            score = HighScore(
                score_id=str(item.get("id", item.get("scoreId", ""))),
                rank=item.get("rank", item.get("position", 0)),
                score=int(item.get("score", 0)),
                player_name=item.get("playerName", item.get("player_name", "Unknown")),
                player_username=item.get("playerUsername", item.get("username", "")),
                player_initials=item.get("playerInitials", item.get("initials", "???")),
                avatar_url=item.get("avatarUrl", item.get("avatar_url")),
            )
            high_scores.append(score)

        # Sort by rank and limit to top 5
        high_scores.sort(key=lambda x: x.rank)
        return high_scores[:5]

    async def get_teams(self) -> list[Team]:
        """Get all teams for the authenticated user."""
        data = await self._request("GET", API_TEAMS_URL)

        teams = []
        for item in data.get("teams", data if isinstance(data, list) else []):
            members = []
            for member_data in item.get("members", []):
                member = TeamMember(
                    user_id=str(member_data.get("id", member_data.get("userId", ""))),
                    username=member_data.get("username", ""),
                    display_name=member_data.get("displayName", member_data.get("name", "")),
                    avatar_url=member_data.get("avatarUrl", member_data.get("avatar_url")),
                )
                members.append(member)

            team = Team(
                team_id=str(item.get("id", item.get("teamId", ""))),
                name=item.get("name", "Unknown Team"),
                members=members,
            )
            teams.append(team)

        return teams

    async def validate_credentials(self) -> bool:
        """Validate the provided credentials."""
        try:
            await self.authenticate()
            return True
        except SternAuthenticationError:
            return False
