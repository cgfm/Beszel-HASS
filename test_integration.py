#!/usr/bin/env python3
"""Test script for Beszel Home Assistant Integration."""

import asyncio
import logging
import sys
from pathlib import Path

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME

# Add the custom component to the path
sys.path.insert(0, str(Path(__file__).parent / "custom_components"))

from beszel.api import BeszelAPIClient  # noqa: E402
from beszel.const import CONF_SSL  # noqa: E402

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)


class MockHomeAssistant:
    """Mock Home Assistant for testing."""

    def __init__(self):
        """Initialize mock HA."""
        self.data = {}


class MockConfigEntry:
    """Mock config entry for testing."""

    def __init__(self, data):
        """Initialize mock config entry."""
        self.data = data
        self.entry_id = "test_entry"


async def test_api_client(host: str, port: int, username: str, password: str, use_ssl: bool = False):
    """Test the API client."""
    print(f"Testing Beszel API Client...")
    print("=" * 50)

    mock_hass = MockHomeAssistant()
    
    client = BeszelAPIClient(
        hass=mock_hass,
        host=host,
        port=port,
        username=username,
        password=password,
        use_ssl=use_ssl,
    )

    try:
        # Test authentication
        print("\n1. Testing authentication...")
        auth_result = await client.authenticate()
        if auth_result:
            print("✅ Authentication successful!")
        else:
            print("❌ Authentication failed!")
            return False

        # Test getting systems
        print("\n2. Testing system retrieval...")
        systems = await client.get_systems()
        print(f"✅ Found {len(systems)} systems")
        
        if systems:
            print("\nSystem details:")
            for i, system in enumerate(systems[:3]):  # Show first 3 systems
                print(f"  System {i+1}:")
                print(f"    ID: {system.get('id', 'N/A')}")
                print(f"    Name: {system.get('name', 'N/A')}")
                print(f"    Status: {system.get('status', 'N/A')}")
                
                # Test getting stats for this system
                system_id = system.get('id')
                if system_id:
                    try:
                        print(f"\n3. Testing stats for system {system_id}...")
                        stats = await client.get_system_stats(system_id)
                        info = stats.get('info', {})
                        print(f"    CPU: {info.get('cpu', 'N/A')}%")
                        print(f"    Memory: {info.get('mp', 'N/A')}%")
                        print(f"    Disk: {info.get('dp', 'N/A')}%")
                    except Exception as e:
                        print(f"    ⚠️  Error getting stats: {e}")

        # Test getting all stats
        print("\n4. Testing bulk stats retrieval...")
        all_stats = await client.get_all_stats()
        print(f"✅ Retrieved stats for {len(all_stats)} systems")
        
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_config_flow(host: str, port: int, username: str, password: str, use_ssl: bool = False):
    """Test the config flow."""
    print(f"\n\nTesting Config Flow...")
    print("=" * 50)
    
    try:
        from beszel.config_flow import validate_input  # noqa: E402
        
        mock_hass = MockHomeAssistant()
        
        user_input = {
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_USERNAME: username,
            CONF_PASSWORD: password,
            CONF_SSL: use_ssl,
        }
        
        print("Testing user input validation...")
        result = await validate_input(mock_hass, user_input)
        
        print(f"✅ Config validation successful!")
        print(f"    Title: {result.get('title', 'N/A')}")
        return True
        
    except Exception as e:
        print(f"❌ Config flow error: {e}")
        return False


def print_installation_instructions():
    """Print installation instructions for Home Assistant."""
    print("\n\nHome Assistant Installation Instructions:")
    print("=" * 60)
    print("""
To test this integration in Home Assistant:

1. Copy the integration to your Home Assistant:
   cp -r custom_components/beszel /config/custom_components/

2. Restart Home Assistant

3. Add the integration:
   - Go to Settings > Devices & Services
   - Click "Add Integration"
   - Search for "Beszel"
   - Enter your Beszel server details

4. Check the entities:
   - Go to Developer Tools > States
   - Look for entities starting with "sensor.beszel_" and "binary_sensor.beszel_"

5. Alternative: Use HACS (if published):
   - Go to HACS > Integrations
   - Add this repository
   - Install the integration
   - Restart Home Assistant
   - Add the integration as above
""")


async def main():
    """Main function."""
    if len(sys.argv) < 5:
        print("Usage: python test_integration.py <host> <port> <username> <password> [use_ssl]")
        print("Example: python test_integration.py localhost 8090 admin password false")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    username = sys.argv[3]
    password = sys.argv[4]
    use_ssl = len(sys.argv) > 5 and sys.argv[5].lower() in ['true', '1', 'yes']

    print("Beszel Home Assistant Integration Test")
    print("=" * 50)
    print(f"Host: {host}:{port}")
    print(f"SSL: {use_ssl}")
    print(f"User: {username}")

    # Test API client
    api_success = await test_api_client(host, port, username, password, use_ssl)
    
    # Test config flow
    config_success = await test_config_flow(host, port, username, password, use_ssl)
    
    print("\n\nTest Summary:")
    print("=" * 30)
    print(f"API Client: {'✅ PASS' if api_success else '❌ FAIL'}")
    print(f"Config Flow: {'✅ PASS' if config_success else '❌ FAIL'}")
    
    if api_success and config_success:
        print("\n🎉 All tests passed! Integration is ready for Home Assistant.")
        print_installation_instructions()
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
