# Stern Insider Connected Home Assistant Integration

## Project Overview

This is a Home Assistant custom integration for displaying Stern Insider Connected pinball leaderboards.

## Technology Stack

- Python 3.12+
- Home Assistant Core integration patterns
- Stern Insider Connected API

## Project Structure

```
custom_components/
  stern_insider_connected/
    __init__.py          # Integration setup
    manifest.json        # Integration manifest
    config_flow.py       # Configuration UI flow
    const.py             # Constants
    coordinator.py       # Data update coordinator
    sensor.py            # Sensor entities
    api.py               # Stern API client
```

## Home Assistant Integration Guidelines

- Follow Home Assistant's [integration development guidelines](https://developers.home-assistant.io/docs/creating_integration_manifest)
- Use `DataUpdateCoordinator` for polling the Stern API
- Implement config flow for UI-based setup
- Store credentials securely using Home Assistant's credential storage

## Code Style

- Follow Home Assistant's code style (black, isort, pylint)
- Use type hints throughout
- All user-facing strings must support localisation

## Testing

- Use pytest with pytest-homeassistant-custom-component
- Test coverage for API client, coordinator, and config flow

## Releasing

To create a new release:

1. **Update version in manifest.json** - Bump the `version` field in `custom_components/stern_insider_connected/manifest.json`
2. **Commit changes** - `git commit -a -m "Release vX.Y.Z"`
3. **Create and push tag** - `git tag vX.Y.Z && git push && git push --tags`
4. **Create GitHub release** - Use `gh release create vX.Y.Z --generate-notes` to create the release with auto-generated release notes
