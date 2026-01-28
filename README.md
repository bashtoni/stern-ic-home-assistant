# Stern Insider Connected for Home Assistant

A Home Assistant custom integration for displaying Stern Insider Connected pinball leaderboards and triggering automations on new high scores.

> **Disclaimer**: This integration is not authorised, endorsed, or affiliated with Stern Pinball, Inc. in any way. "Stern Pinball" and "Stern Insider Connected" are trademarks of Stern Pinball, Inc. Use of this integration is at your own risk.

## Features

- Display high scores from your Stern Insider Connected pinball machines
- Each machine appears as a device with sensors for the top 5 scores (Grand Champion through High Score #4)
- Fire events when new high scores are detected for use in automations
- Configurable polling interval (30 minutes to 24 hours)

## Installation via HACS

1. Ensure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance
2. Open HACS in the Home Assistant sidebar
3. Click the three dots menu in the top right and select **Custom repositories**
4. Add this repository URL and select **Integration** as the category
5. Click **Add**
6. Search for "Stern Insider Connected" in HACS and click **Download**
7. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Stern Insider Connected"
4. Enter your Stern Insider Connected username and password
5. Your pinball machines will appear as devices with high score sensors

### Options

After setup, click **Configure** on the integration to adjust the polling interval.

## Automation Example

Trigger an automation when a new Grand Champion score is set:

```yaml
automation:
  - alias: "Announce new Grand Champion"
    triggers:
      - trigger: event
        event_type: stern_insider_connected_new_high_score
        event_data:
          rank: 1
    actions:
      - action: notify.mobile_app
        data:
          title: "New Grand Champion!"
          message: >
            {{ trigger.event.data.player_name }} scored
            {{ "{:,}".format(trigger.event.data.score) }} on
            {{ trigger.event.data.machine_name }}!
```

### Event Data

The `stern_insider_connected_new_high_score` event includes:

| Field | Description |
|-------|-------------|
| `machine_id` | Unique identifier for the machine |
| `machine_name` | Display name of the machine |
| `score` | The score (integer) |
| `rank` | Position (1 = Grand Champion, 2-5 = High Scores #1-4) |
| `player_name` | Player's display name |
| `player_username` | Player's username |
| `player_initials` | Player's initials |
| `is_new_entry` | Whether this is a new entry on the leaderboard |

## Sensor Attributes

Each high score sensor includes these attributes:

- `rank` - Position on the leaderboard
- `player_name` - Player's display name
- `player_username` - Player's username
- `player_initials` - Player's initials
- `machine_name` - Name of the machine
- `machine_id` - Unique machine identifier
- `avatar_url` - Player's avatar URL (if available)

## Licence

MIT
