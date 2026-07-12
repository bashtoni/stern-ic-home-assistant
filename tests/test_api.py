"""Tests for the Stern Insider Connected API client."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, call, patch

import aiohttp
import pytest

from custom_components.stern_insider_connected.api import (
    SternAPIError,
    SternAuthenticationError,
    SternConnectionError,
    SternInsiderConnectedAPI,
)
from custom_components.stern_insider_connected.const import API_LOGIN_URL

LOGIN_ACTION = "608b67b68d769e8f354b1e1998bdd4cc5108667025"
OLD_LOGIN_ACTION = "9d2cf818afff9e2c69368771b521d93585a10433"
LOGIN_CHUNK_URL = "https://insider.sternpinball.com/_next/static/chunks/login.js"
LOGIN_PAGE = f"""
<script src="https://example.com/untrusted.js"></script>
<script src="{LOGIN_CHUNK_URL}"></script>
"""
LOGIN_CHUNK = (
    f'let login=(0,o.createServerReference)("{LOGIN_ACTION}",o.callServer,'
    'void 0,o.findSourceMapURL,"performLogin");'
)
AUTHENTICATED_RESPONSE = '0:{"a":"$@1"}\n1:{"authenticated":true}'
REJECTED_RESPONSE = (
    '0:{"a":"$@1"}\n'
    '1:{"authenticated":false,"message":"No active user was found with those credentials"}'
)
ACCESS_TOKEN_COOKIE = "spb-insider-token=test-token-123; Path=/; Secure; HttpOnly"


def _response(
    *,
    status: int = 200,
    body: str = "",
    cookies: list[str] | None = None,
) -> MagicMock:
    """Create an asynchronous aiohttp response context manager."""
    response = MagicMock()
    response.status = status
    response.text = AsyncMock(return_value=body)
    response.headers.getall.return_value = cookies or []
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    return response


def _session() -> MagicMock:
    """Create an asynchronous aiohttp session context manager."""
    session = MagicMock()
    session.get = MagicMock()
    session.post = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


def _configure_discovery(session: MagicMock, *, chunk: str = LOGIN_CHUNK) -> None:
    """Configure a session to return the login page and a Next.js chunk."""
    session.get.side_effect = [
        _response(body=LOGIN_PAGE),
        _response(body=chunk),
    ]


class TestSternInsiderConnectedAPI:
    """Tests for SternInsiderConnectedAPI."""

    @pytest.fixture
    def api(self) -> SternInsiderConnectedAPI:
        """Create an API client for testing."""
        return SternInsiderConnectedAPI(
            username="testuser",
            password="testpass",
        )

    @pytest.mark.asyncio
    async def test_authenticate_discovers_action_and_extracts_token(
        self, api: SternInsiderConnectedAPI
    ) -> None:
        """Test successful authentication using the discovered action."""
        session = _session()
        _configure_discovery(session)
        session.post.return_value = _response(
            body=AUTHENTICATED_RESPONSE,
            cookies=[ACCESS_TOKEN_COOKIE],
        )

        with patch("aiohttp.ClientSession", return_value=session):
            result = await api.authenticate()

        assert result is True
        assert api._access_token == "test-token-123"
        assert api._login_action == LOGIN_ACTION
        assert session.get.call_args_list == [
            call(
                API_LOGIN_URL,
                headers={
                    "Accept": "text/html",
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64; rv:142.0) Gecko/20100101 Firefox/142.0"
                    ),
                },
            ),
            call(LOGIN_CHUNK_URL),
        ]
        post_kwargs = session.post.call_args.kwargs
        assert post_kwargs["headers"]["Next-Action"] == LOGIN_ACTION
        assert "Next-Router-State-Tree" not in post_kwargs["headers"]
        assert json.loads(post_kwargs["data"]) == ["testuser", "testpass"]

    @pytest.mark.asyncio
    async def test_authenticate_reuses_cached_action(self, api: SternInsiderConnectedAPI) -> None:
        """Test that a cached action avoids fetching the login bundles."""
        api._login_action = LOGIN_ACTION
        session = _session()
        session.post.return_value = _response(
            body=AUTHENTICATED_RESPONSE,
            cookies=[ACCESS_TOKEN_COOKIE],
        )

        with patch("aiohttp.ClientSession", return_value=session):
            await api.authenticate()

        session.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_rediscovers_stale_action(
        self, api: SternInsiderConnectedAPI
    ) -> None:
        """Test that an obsolete action is rediscovered and retried once."""
        api._login_action = OLD_LOGIN_ACTION
        session = _session()
        _configure_discovery(session)
        session.post.side_effect = [
            _response(body="<!doctype html><html></html>"),
            _response(
                body=AUTHENTICATED_RESPONSE,
                cookies=[ACCESS_TOKEN_COOKIE],
            ),
        ]

        with patch("aiohttp.ClientSession", return_value=session):
            result = await api.authenticate()

        assert result is True
        assert api._login_action == LOGIN_ACTION
        assert [
            request.kwargs["headers"]["Next-Action"] for request in session.post.call_args_list
        ] == [OLD_LOGIN_ACTION, LOGIN_ACTION]

    @pytest.mark.asyncio
    async def test_authenticate_invalid_credentials(self, api: SternInsiderConnectedAPI) -> None:
        """Test a structured credential rejection."""
        session = _session()
        _configure_discovery(session)
        session.post.return_value = _response(body=REJECTED_RESPONSE)

        with (
            patch("aiohttp.ClientSession", return_value=session),
            pytest.raises(SternAuthenticationError, match="No active user"),
        ):
            await api.authenticate()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("status", "message"),
        [(401, "Invalid username or password"), (403, "Account access denied")],
    )
    async def test_authenticate_http_authentication_error(
        self,
        api: SternInsiderConnectedAPI,
        status: int,
        message: str,
    ) -> None:
        """Test HTTP authentication failures."""
        session = _session()
        _configure_discovery(session)
        session.post.return_value = _response(status=status)

        with (
            patch("aiohttp.ClientSession", return_value=session),
            pytest.raises(SternAuthenticationError, match=message),
        ):
            await api.authenticate()

    @pytest.mark.asyncio
    async def test_authenticate_requires_access_token(self, api: SternInsiderConnectedAPI) -> None:
        """Test that a successful response must include an access token."""
        session = _session()
        _configure_discovery(session)
        session.post.return_value = _response(body=AUTHENTICATED_RESPONSE)

        with (
            patch("aiohttp.ClientSession", return_value=session),
            pytest.raises(SternConnectionError, match="without returning an access token"),
        ):
            await api.authenticate()

    @pytest.mark.asyncio
    async def test_authenticate_fails_when_action_cannot_be_discovered(
        self, api: SternInsiderConnectedAPI
    ) -> None:
        """Test a login site whose bundles do not expose performLogin."""
        session = _session()
        _configure_discovery(session, chunk="const unrelated = true;")

        with (
            patch("aiohttp.ClientSession", return_value=session),
            pytest.raises(SternConnectionError, match="Could not discover"),
        ):
            await api.authenticate()

        session.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_retries_malformed_response_once(
        self, api: SternInsiderConnectedAPI
    ) -> None:
        """Test that a malformed response is retried only once."""
        session = _session()
        session.get.side_effect = [
            _response(body=LOGIN_PAGE),
            _response(body=LOGIN_CHUNK),
            _response(body=LOGIN_PAGE),
            _response(body=LOGIN_CHUNK),
        ]
        session.post.side_effect = [
            _response(body="<!doctype html>"),
            _response(body="<!doctype html>"),
        ]

        with (
            patch("aiohttp.ClientSession", return_value=session),
            pytest.raises(SternConnectionError, match="unexpected response"),
        ):
            await api.authenticate()

        assert session.post.call_count == 2

    @pytest.mark.asyncio
    async def test_authenticate_connection_error(self, api: SternInsiderConnectedAPI) -> None:
        """Test a connection failure while loading the login page."""
        session = _session()
        session.get.side_effect = aiohttp.ClientConnectionError("offline")

        with (
            patch("aiohttp.ClientSession", return_value=session),
            pytest.raises(SternConnectionError, match="Failed to connect"),
        ):
            await api.authenticate()

    @pytest.mark.asyncio
    async def test_validate_credentials_success(self, api: SternInsiderConnectedAPI) -> None:
        """Test validating credentials successfully."""
        with patch.object(api, "authenticate", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = True
            result = await api.validate_credentials()
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_credentials_failure(self, api: SternInsiderConnectedAPI) -> None:
        """Test validating credentials with failure."""
        with patch.object(api, "authenticate", new_callable=AsyncMock) as mock_auth:
            mock_auth.side_effect = SternAuthenticationError("Invalid credentials")
            result = await api.validate_credentials()
            assert result is False

    def test_is_token_valid_no_token(self, api: SternInsiderConnectedAPI) -> None:
        """Test token validity without a token."""
        assert api._is_token_valid() is False

    def test_is_token_valid_expired(self, api: SternInsiderConnectedAPI) -> None:
        """Test token validity when it has expired."""
        api._access_token = "test-token"
        api._token_expiry = 0
        assert api._is_token_valid() is False


class TestAPIExceptions:
    """Tests for API exceptions."""

    def test_stern_api_error(self) -> None:
        """Test SternAPIError."""
        error = SternAPIError("Test error")
        assert str(error) == "Test error"

    def test_stern_authentication_error(self) -> None:
        """Test SternAuthenticationError."""
        error = SternAuthenticationError("Auth failed")
        assert str(error) == "Auth failed"
        assert isinstance(error, SternAPIError)

    def test_stern_connection_error(self) -> None:
        """Test SternConnectionError."""
        error = SternConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, SternAPIError)
