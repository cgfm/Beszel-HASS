"""Test configuration for Beszel integration."""
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.beszel.const import DOMAIN, CONF_SSL, DEFAULT_PORT, DEFAULT_SSL


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "test.example.com",
            "port": DEFAULT_PORT,
            "username": "testuser",
            "password": "testpass",
            "use_ssl": DEFAULT_SSL,
        },
        unique_id="test_beszel_instance",
    )


@pytest.fixture
async def setup_integration(hass: HomeAssistant, mock_config_entry):
    """Set up the Beszel integration."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry


@pytest.fixture
def mock_beszel_api():
    """Mock Beszel API responses."""
    return {
        "systems": [
            {
                "id": "system1",
                "name": "Test Server 1",
                "os": "Linux",
                "arch": "x64",
                "version": "1.0.0"
            }
        ],
        "stats": {
            "cpu": {"usage": 45.2},
            "memory": {"used": 8589934592, "total": 17179869184, "free": 8589934592},
            "disk": {"used": 107374182400, "total": 214748364800, "free": 107374182400},
            "network": {"upload": 1048576, "download": 2097152},
            "temperature": {"main": 65.5},
            "uptime": 86400,
            "timestamp": "2025-06-30T12:00:00Z"
        }
    }
