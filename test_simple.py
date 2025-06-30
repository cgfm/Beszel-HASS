#!/usr/bin/env python3
"""Simple test script for Beszel integration components."""

import asyncio
import logging
import sys
from pathlib import Path

import aiohttp

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)


async def test_direct_api(host: str, port: int, username: str, password: str, use_ssl: bool = False):
    """Test the API directly without Home Assistant dependencies."""
    scheme = "https" if use_ssl else "http"
    base_url = f"{scheme}://{host}:{port}"
    
    print(f"Testing direct API access to: {base_url}")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test authentication
            print("\n1. Testing authentication...")
            auth_data = {"identity": username, "password": password}
            
            async with session.post(
                f"{base_url}/api/collections/users/auth-with-password",
                json=auth_data,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    token = data.get("token")
                    print("✅ Authentication successful!")
                    print(f"   Token: {token[:50]}..." if token else "No token")
                else:
                    print(f"❌ Authentication failed: {response.status}")
                    return False
            
            # Test getting systems
            print("\n2. Testing systems retrieval...")
            headers = {"Authorization": f"Bearer {token}"}
            
            async with session.get(
                f"{base_url}/api/collections/systems/records",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    systems = data.get("items", [])
                    print(f"✅ Found {len(systems)} systems")
                    
                    for i, system in enumerate(systems[:3]):
                        print(f"   System {i+1}:")
                        print(f"     ID: {system.get('id', 'N/A')}")
                        print(f"     Name: {system.get('name', 'N/A')}")
                        print(f"     Status: {system.get('status', 'N/A')}")
                        
                        # Show info if available
                        info = system.get('info', {})
                        if info:
                            print(f"     CPU: {info.get('cpu', 'N/A')}%")
                            print(f"     Memory: {info.get('mp', 'N/A')}%")
                            print(f"     Disk: {info.get('dp', 'N/A')}%")
                
                    return True
                else:
                    print(f"❌ Systems retrieval failed: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return False


def check_integration_files():
    """Check if all integration files are present."""
    print("Checking integration files...")
    print("=" * 50)
    
    required_files = [
        "custom_components/beszel/__init__.py",
        "custom_components/beszel/manifest.json",
        "custom_components/beszel/config_flow.py",
        "custom_components/beszel/api.py",
        "custom_components/beszel/coordinator.py",
        "custom_components/beszel/sensor.py",
        "custom_components/beszel/binary_sensor.py",
        "custom_components/beszel/const.py",
        "custom_components/beszel/strings.py",
        "custom_components/beszel/translations/en.json",
        "custom_components/beszel/translations/de.json",
    ]
    
    missing_files = []
    present_files = []
    
    for file_path in required_files:
        if Path(file_path).exists():
            present_files.append(file_path)
            print(f"✅ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"❌ {file_path}")
    
    print(f"\nSummary: {len(present_files)} present, {len(missing_files)} missing")
    
    if missing_files:
        print("Missing files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    return True


def check_hacs_compliance():
    """Check HACS compliance."""
    print("\n\nChecking HACS compliance...")
    print("=" * 50)
    
    checks = []
    
    # Check manifest.json
    manifest_path = Path("custom_components/beszel/manifest.json")
    if manifest_path.exists():
        import json
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        required_fields = ["domain", "name", "documentation", "issue_tracker", "codeowners"]
        for field in required_fields:
            if field in manifest:
                checks.append(f"✅ manifest.json has '{field}'")
            else:
                checks.append(f"❌ manifest.json missing '{field}'")
    else:
        checks.append("❌ manifest.json not found")
    
    # Check hacs.json
    hacs_path = Path("hacs.json")
    if hacs_path.exists():
        import json
        with open(hacs_path) as f:
            hacs_data = json.load(f)
        
        required_fields = ["name", "hacs", "homeassistant"]
        for field in required_fields:
            if field in hacs_data:
                checks.append(f"✅ hacs.json has '{field}'")
            else:
                checks.append(f"❌ hacs.json missing '{field}'")
    else:
        checks.append("❌ hacs.json not found")
    
    # Check README
    if Path("README.md").exists():
        checks.append("✅ README.md exists")
    else:
        checks.append("❌ README.md missing")
    
    # Check LICENSE
    if Path("LICENSE").exists():
        checks.append("✅ LICENSE exists")
    else:
        checks.append("❌ LICENSE missing")
    
    for check in checks:
        print(check)
    
    return all("✅" in check for check in checks)


def print_next_steps():
    """Print next steps for deployment."""
    print("\n\nNext Steps for Deployment:")
    print("=" * 50)
    print("""
1. Test in Home Assistant:
   - Copy custom_components/beszel to your HA config/custom_components/
   - Restart Home Assistant
   - Go to Settings > Devices & Services > Add Integration
   - Search for "Beszel" and configure

2. Prepare for HACS:
   - Create GitHub repository
   - Update URLs in manifest.json and hacs.json
   - Add proper description and topics to GitHub repo
   - Test installation via HACS custom repository

3. Request HACS inclusion:
   - Submit PR to HACS/default repository
   - Follow HACS guidelines: https://hacs.xyz/docs/publish/include

4. Optional improvements:
   - Add more sensor types (network, temperature, etc.)
   - Add device triggers for alerts
   - Add config options for update intervals
   - Add support for historical statistics
""")


async def main():
    """Main function."""
    print("Beszel Home Assistant Integration - Readiness Check")
    print("=" * 60)
    
    # Check files
    files_ok = check_integration_files()
    
    # Check HACS compliance
    hacs_ok = check_hacs_compliance()
    
    # Test API if credentials provided
    api_ok = False
    if len(sys.argv) >= 5:
        host = sys.argv[1]
        port = int(sys.argv[2])
        username = sys.argv[3]
        password = sys.argv[4]
        use_ssl = len(sys.argv) > 5 and sys.argv[5].lower() in ['true', '1', 'yes']
        
        api_ok = await test_direct_api(host, port, username, password, use_ssl)
    else:
        print("\n\nAPI Test Skipped:")
        print("=" * 50)
        print("To test API: python test_simple.py <host> <port> <username> <password> [use_ssl]")
        print("Example: python test_simple.py localhost 8090 admin password false")
    
    # Summary
    print("\n\nReadiness Summary:")
    print("=" * 30)
    print(f"Files Present: {'✅ PASS' if files_ok else '❌ FAIL'}")
    print(f"HACS Compliant: {'✅ PASS' if hacs_ok else '❌ FAIL'}")
    if len(sys.argv) >= 5:
        print(f"API Working: {'✅ PASS' if api_ok else '❌ FAIL'}")
    
    overall_ready = files_ok and hacs_ok and (api_ok if len(sys.argv) >= 5 else True)
    
    if overall_ready:
        print("\n🎉 Integration is ready for deployment!")
        print_next_steps()
    else:
        print("\n⚠️  Integration needs fixes before deployment.")


if __name__ == "__main__":
    asyncio.run(main())
