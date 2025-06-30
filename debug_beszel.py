#!/usr/bin/env python3
"""Debug script to test Beszel API connection."""

import asyncio
import json
import sys
from typing import Any, Dict

import aiohttp


async def test_beszel_connection(host: str, port: int, username: str, password: str, use_ssl: bool = False):
    """Test connection to Beszel API."""
    scheme = "https" if use_ssl else "http"
    base_url = f"{scheme}://{host}:{port}"
    
    print(f"Testing connection to: {base_url}")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Basic connectivity
        print("\n1. Testing basic connectivity...")
        try:
            async with session.get(f"{base_url}", timeout=aiohttp.ClientTimeout(total=10)) as response:
                print(f"   Status: {response.status}")
                if response.status == 200:
                    print("   ✅ Server is reachable")
                elif response.status in [401, 403]:
                    print("   ✅ Server is reachable (authentication required)")
                else:
                    print(f"   ⚠️  Unexpected status: {response.status}")
        except Exception as e:
            print(f"   ❌ Connection failed: {e}")
            return
        
        # Test 2: API endpoints discovery
        print("\n2. Testing API endpoints...")
        
        endpoints_to_test = [
            "/api",
            "/api/ping",
            "/api/health",
            "/api/status",
            "/api/auth/login",
            "/api/login",
            "/api/systems",
            "/api/nodes",
        ]
        
        for endpoint in endpoints_to_test:
            try:
                async with session.get(f"{base_url}{endpoint}", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    print(f"   {endpoint}: {response.status}")
            except Exception as e:
                print(f"   {endpoint}: ERROR - {e}")
        
        # Test 3: Authentication
        print("\n3. Testing authentication...")
        auth_data = {
            "username": username,
            "password": password
        }
        
        auth_endpoints = ["/api/auth/login", "/api/login"]
        auth_success = False
        token = None
        
        for endpoint in auth_endpoints:
            try:
                print(f"   Trying {endpoint}...")
                async with session.post(
                    f"{base_url}{endpoint}",
                    json=auth_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    print(f"   Status: {response.status}")
                    if response.status == 200:
                        try:
                            result = await response.json()
                            print(f"   Response: {json.dumps(result, indent=2)}")
                            token = result.get("token") or result.get("access_token")
                            if token:
                                print(f"   ✅ Authentication successful, token received")
                                auth_success = True
                                break
                            else:
                                print("   ⚠️  No token in response")
                        except Exception as e:
                            print(f"   ⚠️  Could not parse JSON response: {e}")
                    elif response.status == 401:
                        print("   ❌ Invalid credentials")
                    elif response.status == 404:
                        print("   ⚠️  Endpoint not found, trying next...")
                    else:
                        print(f"   ⚠️  Unexpected status: {response.status}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        if not auth_success:
            print("\n❌ Authentication failed with all endpoints")
            return
        
        # Test 4: Get systems/nodes
        print("\n4. Testing systems/nodes endpoints...")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        systems_endpoints = ["/api/systems", "/api/nodes"]
        
        for endpoint in systems_endpoints:
            try:
                print(f"   Trying {endpoint}...")
                async with session.get(
                    f"{base_url}{endpoint}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    print(f"   Status: {response.status}")
                    if response.status == 200:
                        try:
                            result = await response.json()
                            print(f"   Response: {json.dumps(result, indent=2)}")
                            print(f"   ✅ Found {len(result) if isinstance(result, list) else 'unknown number of'} systems")
                            break
                        except Exception as e:
                            print(f"   ⚠️  Could not parse JSON response: {e}")
                    elif response.status == 404:
                        print("   ⚠️  Endpoint not found, trying next...")
                    else:
                        print(f"   ⚠️  Unexpected status: {response.status}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print("\n" + "=" * 50)
        print("Test completed!")


def main():
    """Main function."""
    if len(sys.argv) < 5:
        print("Usage: python debug_beszel.py <host> <port> <username> <password> [use_ssl]")
        print("Example: python debug_beszel.py localhost 8090 admin password false")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    username = sys.argv[3]
    password = sys.argv[4]
    use_ssl = len(sys.argv) > 5 and sys.argv[5].lower() in ['true', '1', 'yes']
    
    asyncio.run(test_beszel_connection(host, port, username, password, use_ssl))


if __name__ == "__main__":
    main()
