#!/usr/bin/env python3
"""Simple debug script to test Beszel API connection using requests."""

import json
import sys
from typing import Any, Dict

import requests


def test_beszel_connection(
    host: str, port: int, username: str, password: str, use_ssl: bool = False
):
    """Test connection to Beszel API."""
    scheme = "https" if use_ssl else "http"
    base_url = f"{scheme}://{host}:{port}"

    print(f"Testing connection to: {base_url}")
    print("=" * 50)

    # Configure session
    session = requests.Session()
    session.timeout = 10

    # Test 1: Basic connectivity
    print("\n1. Testing basic connectivity...")
    try:
        response = session.get(f"{base_url}")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Server is reachable")
        elif response.status_code in [401, 403]:
            print("   ✅ Server is reachable (authentication required)")
        else:
            print(f"   ⚠️  Unexpected status: {response.status_code}")
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
        "/api/server",
        "/api/servers",
    ]

    for endpoint in endpoints_to_test:
        try:
            response = session.get(f"{base_url}{endpoint}", timeout=5)
            print(f"   {endpoint}: {response.status_code}")
            if response.status_code == 200 and endpoint in ["/api", "/api/status"]:
                try:
                    data = response.json()
                    print(f"      Response: {json.dumps(data, indent=6)}")
                except:
                    print(f"      Response (text): {response.text[:100]}...")
        except Exception as e:
            print(f"   {endpoint}: ERROR - {str(e)[:50]}...")

    # Test 3: Authentication
    print("\n3. Testing authentication...")
    auth_data = {"username": username, "password": password}

    # Try different authentication formats
    auth_formats = [
        ("JSON", auth_data),
        ("email/password", {"email": username, "password": password}),
        ("user/pass", {"user": username, "pass": password}),
    ]

    auth_endpoints = ["/api/auth/login", "/api/login", "/api/auth", "/login"]
    auth_success = False
    token = None

    for endpoint in auth_endpoints:
        print(f"\n   Trying endpoint: {endpoint}")
        for format_name, data in auth_formats:
            try:
                print(f"     Format: {format_name}")
                response = session.post(
                    f"{base_url}{endpoint}",
                    json=data,
                    headers={"Content-Type": "application/json"},
                    timeout=10,
                )
                print(f"     Status: {response.status_code}")
                if response.status_code == 200:
                    try:
                        result = response.json()
                        print(f"     Response: {json.dumps(result, indent=8)}")
                        token = (
                            result.get("token")
                            or result.get("access_token")
                            or result.get("jwt")
                        )
                        if token:
                            print(f"     ✅ Authentication successful, token received")
                            auth_success = True
                            break
                        else:
                            print("     ⚠️  No token in response")
                    except Exception as e:
                        print(f"     ⚠️  Could not parse JSON response: {e}")
                        print(f"     Raw response: {response.text[:200]}...")
                elif response.status_code == 401:
                    print("     ❌ Invalid credentials")
                elif response.status_code == 404:
                    print("     ⚠️  Endpoint not found")
                elif response.status_code == 405:
                    print("     ⚠️  Method not allowed (try GET?)")
                    # Try GET for this endpoint
                    try:
                        get_response = session.get(f"{base_url}{endpoint}")
                        print(f"     GET Status: {get_response.status_code}")
                    except:
                        pass
                else:
                    print(f"     ⚠️  Unexpected status: {response.status_code}")
                    print(f"     Response: {response.text[:200]}...")
            except Exception as e:
                print(f"     ❌ Error: {e}")

        if auth_success:
            break

    if not auth_success:
        print("\n❌ Authentication failed with all endpoints and formats")
        print("\nTrying alternative approaches...")

        # Try basic auth
        try:
            print("\n   Trying HTTP Basic Auth...")
            response = session.get(
                f"{base_url}/api/systems", auth=(username, password), timeout=10
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Basic Auth successful!")
                try:
                    result = response.json()
                    print(f"   Systems: {json.dumps(result, indent=4)}")
                except:
                    print(f"   Response: {response.text[:200]}...")
                return
        except Exception as e:
            print(f"   ❌ Basic Auth failed: {e}")

        return

    # Test 4: Get systems/nodes
    print("\n4. Testing systems/nodes endpoints...")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    systems_endpoints = ["/api/systems", "/api/nodes", "/api/servers", "/api/hosts"]

    for endpoint in systems_endpoints:
        try:
            print(f"   Trying {endpoint}...")
            response = session.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"   Response: {json.dumps(result, indent=4)}")
                    print(
                        f"   ✅ Found {len(result) if isinstance(result, list) else 'unknown number of'} systems"
                    )
                    break
                except Exception as e:
                    print(f"   ⚠️  Could not parse JSON response: {e}")
                    print(f"   Raw response: {response.text[:200]}...")
            elif response.status_code == 404:
                print("   ⚠️  Endpoint not found, trying next...")
            else:
                print(f"   ⚠️  Unexpected status: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n" + "=" * 50)
    print("Test completed!")


def main():
    """Main function."""
    if len(sys.argv) < 5:
        print(
            "Usage: python debug_beszel_simple.py <host> <port> <username> <password> [use_ssl]"
        )
        print(
            "Example: python debug_beszel_simple.py localhost 8090 admin password false"
        )
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    username = sys.argv[3]
    password = sys.argv[4]
    use_ssl = len(sys.argv) > 5 and sys.argv[5].lower() in ["true", "1", "yes"]

    test_beszel_connection(host, port, username, password, use_ssl)


if __name__ == "__main__":
    main()
