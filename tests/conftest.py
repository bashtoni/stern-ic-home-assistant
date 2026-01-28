"""Fixtures for Stern Insider Connected tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.stern_insider_connected.models import HighScore, Machine


@pytest.fixture
def mock_machines() -> list[Machine]:
    """Return mock machine data."""
    return [
        Machine(
            machine_id="machine-123",
            name="Test Machine",
            game_title="Godzilla",
            image_url="https://example.com/godzilla.jpg",
            high_scores=[],
        ),
        Machine(
            machine_id="machine-456",
            name="Another Machine",
            game_title="Venom",
            image_url="https://example.com/venom.jpg",
            high_scores=[],
        ),
    ]


@pytest.fixture
def mock_high_scores() -> list[HighScore]:
    """Return mock high score data."""
    return [
        HighScore(
            score_id="score-1",
            rank=1,
            score=1_500_000_000,
            player_name="Grand Champion",
            player_username="gc_player",
            player_initials="GC",
            avatar_url="https://example.com/gc.jpg",
        ),
        HighScore(
            score_id="score-2",
            rank=2,
            score=1_200_000_000,
            player_name="High Score One",
            player_username="hs1_player",
            player_initials="HS1",
            avatar_url=None,
        ),
        HighScore(
            score_id="score-3",
            rank=3,
            score=900_000_000,
            player_name="High Score Two",
            player_username="hs2_player",
            player_initials="HS2",
            avatar_url=None,
        ),
        HighScore(
            score_id="score-4",
            rank=4,
            score=600_000_000,
            player_name="High Score Three",
            player_username="hs3_player",
            player_initials="HS3",
            avatar_url=None,
        ),
        HighScore(
            score_id="score-5",
            rank=5,
            score=300_000_000,
            player_name="High Score Four",
            player_username="hs4_player",
            player_initials="HS4",
            avatar_url=None,
        ),
    ]


@pytest.fixture
def mock_api() -> Generator[AsyncMock, None, None]:
    """Mock the Stern API client."""
    with patch(
        "custom_components.stern_insider_connected.api.SternInsiderConnectedAPI",
        autospec=True,
    ) as mock:
        client = mock.return_value
        client.authenticate = AsyncMock(return_value=True)
        client.validate_credentials = AsyncMock(return_value=True)
        client.get_machines = AsyncMock(return_value=[])
        client.get_high_scores = AsyncMock(return_value=[])
        client.close = AsyncMock()
        yield client
