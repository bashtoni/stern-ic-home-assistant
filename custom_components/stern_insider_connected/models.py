"""Data models for the Stern Insider Connected integration."""

from dataclasses import dataclass, field


@dataclass
class HighScore:
    """Represents a high score entry."""

    score_id: str
    rank: int
    score: int
    player_name: str
    player_username: str
    player_initials: str
    avatar_url: str | None = None


@dataclass
class Machine:
    """Represents a pinball machine."""

    machine_id: str
    name: str
    game_title: str
    image_url: str | None = None
    high_scores: list[HighScore] = field(default_factory=list)


@dataclass
class TeamMember:
    """Represents a team member."""

    user_id: str
    username: str
    display_name: str
    avatar_url: str | None = None


@dataclass
class Team:
    """Represents a team/venue."""

    team_id: str
    name: str
    members: list[TeamMember] = field(default_factory=list)
