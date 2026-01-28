"""Tests for the Stern Insider Connected data models."""

from __future__ import annotations

from custom_components.stern_insider_connected.models import (
    HighScore,
    Machine,
    Team,
    TeamMember,
)


class TestHighScore:
    """Tests for HighScore model."""

    def test_create_high_score(self) -> None:
        """Test creating a high score."""
        score = HighScore(
            score_id="score-123",
            rank=1,
            score=1_500_000_000,
            player_name="Test Player",
            player_username="testplayer",
            player_initials="TP",
            avatar_url="https://example.com/avatar.jpg",
        )

        assert score.score_id == "score-123"
        assert score.rank == 1
        assert score.score == 1_500_000_000
        assert score.player_name == "Test Player"
        assert score.player_username == "testplayer"
        assert score.player_initials == "TP"
        assert score.avatar_url == "https://example.com/avatar.jpg"

    def test_create_high_score_without_avatar(self) -> None:
        """Test creating a high score without avatar URL."""
        score = HighScore(
            score_id="score-123",
            rank=1,
            score=1_000_000,
            player_name="Test Player",
            player_username="testplayer",
            player_initials="TP",
        )

        assert score.avatar_url is None


class TestMachine:
    """Tests for Machine model."""

    def test_create_machine(self) -> None:
        """Test creating a machine."""
        machine = Machine(
            machine_id="machine-123",
            name="My Godzilla",
            game_title="Godzilla",
            image_url="https://example.com/godzilla.jpg",
        )

        assert machine.machine_id == "machine-123"
        assert machine.name == "My Godzilla"
        assert machine.game_title == "Godzilla"
        assert machine.image_url == "https://example.com/godzilla.jpg"
        assert machine.high_scores == []

    def test_create_machine_with_high_scores(self) -> None:
        """Test creating a machine with high scores."""
        scores = [
            HighScore(
                score_id="score-1",
                rank=1,
                score=1_000_000,
                player_name="Player 1",
                player_username="player1",
                player_initials="P1",
            ),
        ]

        machine = Machine(
            machine_id="machine-123",
            name="My Godzilla",
            game_title="Godzilla",
            high_scores=scores,
        )

        assert len(machine.high_scores) == 1
        assert machine.high_scores[0].score == 1_000_000


class TestTeamMember:
    """Tests for TeamMember model."""

    def test_create_team_member(self) -> None:
        """Test creating a team member."""
        member = TeamMember(
            user_id="user-123",
            username="testuser",
            display_name="Test User",
            avatar_url="https://example.com/avatar.jpg",
        )

        assert member.user_id == "user-123"
        assert member.username == "testuser"
        assert member.display_name == "Test User"
        assert member.avatar_url == "https://example.com/avatar.jpg"


class TestTeam:
    """Tests for Team model."""

    def test_create_team(self) -> None:
        """Test creating a team."""
        members = [
            TeamMember(
                user_id="user-1",
                username="user1",
                display_name="User One",
            ),
            TeamMember(
                user_id="user-2",
                username="user2",
                display_name="User Two",
            ),
        ]

        team = Team(
            team_id="team-123",
            name="Test Team",
            members=members,
        )

        assert team.team_id == "team-123"
        assert team.name == "Test Team"
        assert len(team.members) == 2
