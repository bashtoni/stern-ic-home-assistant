"""Constants for the Stern Insider Connected integration."""

from typing import Final

DOMAIN: Final = "stern_insider_connected"

# API URLs
API_BASE_URL: Final = "https://api.sternpinball.com"
API_LOGIN_URL: Final = f"{API_BASE_URL}/api/login"
API_MACHINES_URL: Final = f"{API_BASE_URL}/api/machines"
API_HIGH_SCORES_URL: Final = f"{API_BASE_URL}/api/venuemachines/{{machine_id}}/highscores"
API_TEAMS_URL: Final = f"{API_BASE_URL}/api/teams"

# Configuration keys
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_SCAN_INTERVAL: Final = "scan_interval"

# Default values
DEFAULT_SCAN_INTERVAL: Final = 30  # minutes
MIN_SCAN_INTERVAL: Final = 30  # minutes
MAX_SCAN_INTERVAL: Final = 1440  # minutes (24 hours)

# Token management
TOKEN_EXPIRY_BUFFER: Final = 300  # seconds (5 minutes before expiry)

# High score ranks
HIGH_SCORE_COUNT: Final = 5
HIGH_SCORE_NAMES: Final = {
    1: "Grand Champion",
    2: "High Score #1",
    3: "High Score #2",
    4: "High Score #3",
    5: "High Score #4",
}

# Events
EVENT_NEW_HIGH_SCORE: Final = "stern_insider_connected_new_high_score"
