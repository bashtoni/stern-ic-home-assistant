"""API client for Stern Insider Connected."""

from __future__ import annotations

import json
import logging
import re
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
        self._cookies: list[str] = []
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
        """Authenticate with the Stern API via website login."""
        session = await self._ensure_session()

        # Headers required for Next.js server action
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:142.0) Gecko/20100101 Firefox/142.0",
            "Accept": "text/x-component",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://insider.sternpinball.com/login",
            "Next-Action": "9d2cf818afff9e2c69368771b521d93585a10433",
            "Next-Router-State-Tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22login%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2C%22%2Flogin%22%2C%22refresh%22%5D%7D%5D%7D%2Cnull%2Cnull%2Ctrue%5D",
            "Content-Type": "text/plain;charset=UTF-8",
            "Origin": "https://insider.sternpinball.com",
        }

        # Login data sent as JSON array (not object)
        login_data = json.dumps([self._username, self._password])

        try:
            async with session.post(
                API_LOGIN_URL,
                headers=headers,
                data=login_data,
                allow_redirects=False,
            ) as response:
                # Extract token from cookies
                token = None
                cookies = response.headers.getall("Set-Cookie", [])
                for cookie in cookies:
                    if "spb-insider-token=" in cookie:
                        # Extract token value
                        match = re.search(r"spb-insider-token=([^;]+)", cookie)
                        if match:
                            token = match.group(1)
                            break

                # Check response body for authentication status
                response_text = await response.text()
                authenticated = False
                if '"authenticated"' in response_text:
                    try:
                        for line in response_text.split("\n"):
                            if '"authenticated"' in line:
                                json_match = re.search(r"\{.*\}", line)
                                if json_match:
                                    auth_result = json.loads(json_match.group(0))
                                    authenticated = auth_result.get("authenticated", False)
                                    break
                    except (json.JSONDecodeError, AttributeError):
                        pass

                if response.status == 200 and (authenticated or token):
                    self._access_token = token
                    self._cookies = cookies
                    # Token expires in 30 minutes
                    self._token_expiry = time.time() + 1800

                    _LOGGER.debug("Successfully authenticated with Stern API")
                    return True

                if response.status == 401:
                    raise SternAuthenticationError("Invalid username or password")
                if response.status == 403:
                    raise SternAuthenticationError("Account access denied")

                raise SternAuthenticationError(
                    f"Authentication failed - status {response.status}, authenticated={authenticated}, has_token={token is not None}"
                )

        except aiohttp.ClientError as err:
            raise SternConnectionError(f"Failed to connect to Stern API: {err}") from err

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid authentication token."""
        if not self._is_token_valid():
            await self.authenticate()

    def _get_api_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        return {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:142.0) Gecko/20100101 Firefox/142.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://insider.sternpinball.com/",
            "Content-Type": "application/json",
            "Origin": "https://insider.sternpinball.com",
            "Authorization": f"Bearer {self._access_token}",
        }

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> Any:
        """Make an authenticated request to the API."""
        await self._ensure_authenticated()
        session = await self._ensure_session()

        headers = self._get_api_headers()
        headers.update(kwargs.pop("headers", {}))

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
        url = f"{API_MACHINES_URL}?group_type=home"
        data = await self._request("GET", url)

        machines = []
        # Response format: {"user": {"machines": [...]}}
        user_data = data.get("user", {})
        machines_list = user_data.get("machines", data.get("machines", []))

        for item in machines_list:
            # Get model info for game title
            model = item.get("model", {})
            game_title = model.get("name", item.get("name", "Unknown"))

            machine = Machine(
                machine_id=str(item.get("id", "")),
                name=item.get("nickname", item.get("name", game_title)),
                game_title=game_title,
                image_url=model.get("image_url", item.get("image_url")),
            )
            machines.append(machine)

        return machines

    async def get_high_scores(self, machine_id: str) -> list[HighScore]:
        """Get high scores for a specific machine."""
        url = f"{API_HIGH_SCORES_URL}?machine_id={machine_id}"
        data = await self._request("GET", url)

        high_scores = []
        # Response can be a list directly or have a wrapper
        scores_list: list[dict[str, Any]] = (
            data if isinstance(data, list) else data.get("high_scores", data.get("scores", []))
        )

        for idx, item in enumerate(scores_list):
            # Get user info
            user: dict[str, Any] = item.get("user", {})
            score = HighScore(
                score_id=str(item.get("id", "")),
                rank=item.get("rank", item.get("position", idx + 1)),
                score=int(item.get("score", 0)),
                player_name=user.get("full_name", user.get("username", "Unknown")),
                player_username=user.get("username", ""),
                player_initials=item.get("initials", user.get("initials", "???")),
                avatar_url=user.get("avatar_url"),
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
