"""Tests for the Stern Insider Connected API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.stern_insider_connected.api import (
    SternAPIError,
    SternAuthenticationError,
    SternConnectionError,
    SternInsiderConnectedAPI,
)


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
    async def test_authenticate_success(self, api: SternInsiderConnectedAPI) -> None:
        """Test successful authentication."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "accessToken": "test-token-123",
                "expiresIn": 1800,
            }
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            result = await api.authenticate()

            assert result is True
            assert api._access_token == "test-token-123"

    @pytest.mark.asyncio
    async def test_authenticate_invalid_credentials(
        self, api: SternInsiderConnectedAPI
    ) -> None:
        """Test authentication with invalid credentials."""
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            with pytest.raises(SternAuthenticationError):
                await api.authenticate()

    @pytest.mark.asyncio
    async def test_validate_credentials_success(
        self, api: SternInsiderConnectedAPI
    ) -> None:
        """Test validating credentials successfully."""
        with patch.object(api, "authenticate", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = True
            result = await api.validate_credentials()
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_credentials_failure(
        self, api: SternInsiderConnectedAPI
    ) -> None:
        """Test validating credentials with failure."""
        with patch.object(api, "authenticate", new_callable=AsyncMock) as mock_auth:
            mock_auth.side_effect = SternAuthenticationError("Invalid credentials")
            result = await api.validate_credentials()
            assert result is False

    def test_is_token_valid_no_token(self, api: SternInsiderConnectedAPI) -> None:
        """Test token validity check with no token."""
        assert api._is_token_valid() is False

    def test_is_token_valid_expired(self, api: SternInsiderConnectedAPI) -> None:
        """Test token validity check with expired token."""
        api._access_token = "test-token"
        api._token_expiry = 0  # Expired
        assert api._is_token_valid() is False


class TestAPIExceptions:
    """Tests for API exceptions."""

    def test_stern_api_error(self) -> None:
        """Test SternAPIError exception."""
        error = SternAPIError("Test error")
        assert str(error) == "Test error"

    def test_stern_authentication_error(self) -> None:
        """Test SternAuthenticationError exception."""
        error = SternAuthenticationError("Auth failed")
        assert str(error) == "Auth failed"
        assert isinstance(error, SternAPIError)

    def test_stern_connection_error(self) -> None:
        """Test SternConnectionError exception."""
        error = SternConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, SternAPIError)
