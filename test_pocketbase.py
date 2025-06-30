#!/usr/bin/env python3
"""Test PocketBase authentication for Beszel."""

import json
import sys
import requests


def test_pocketbase_auth(host: str, port: int, username: str, password: str, use_ssl: bool = False):
    """Test PocketBase authentication."""
    scheme = "https" if use_ssl else "http"
    base_url = f"{scheme}://{host}:{port}"
    
    print(f"Testing PocketBase authentication to: {base_url}")
    print("=" * 50)
    
    session = requests.Session()
    session.timeout = 10
    
    # Test 1: Get collections info
    print("\n1. Testing PocketBase API...")
    try:
        response = session.get(f"{base_url}/api/collections")
        print(f"   Collections endpoint status: {response.status_code}")
        if response.status_code == 200:
            collections = response.json()
            print(f"   Found {len(collections.get('items', []))} collections")
            for item in collections.get('items', [])[:5]:  # Show first 5
                print(f"     - {item.get('name', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Collections test failed: {e}")
    
    # Test 2: Try authentication with different collection names
    auth_collections = ["users", "_superusers", "admins", "accounts"]
    
    for collection in auth_collections:
        print(f"\n2. Testing authentication with collection '{collection}'...")
        
        try:
            # Try PocketBase auth with password endpoint
            auth_url = f"{base_url}/api/collections/{collection}/auth-with-password"
            auth_data = {
                "identity": username,
                "password": password
            }
            
            response = session.post(auth_url, json=auth_data)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Authentication successful with collection '{collection}'!")
                print(f"   Token: {result.get('token', 'no token')[:50]}...")
                print(f"   User: {result.get('record', {}).get('email', 'no email')}")
                
                # Test API access with token
                token = result.get('token')
                if token:
                    print(f"\n3. Testing API access with token...")
                    headers = {"Authorization": f"Bearer {token}"}
                    
                    # Try to get systems data
                    test_endpoints = [
                        "/api/collections/systems/records",
                        "/api/collections/nodes/records", 
                        "/api/collections/servers/records",
                        "/api/collections/hosts/records",
                    ]
                    
                    for endpoint in test_endpoints:
                        try:
                            response = session.get(f"{base_url}{endpoint}", headers=headers)
                            print(f"   {endpoint}: {response.status_code}")
                            if response.status_code == 200:
                                data = response.json()
                                items = data.get('items', [])
                                print(f"     Found {len(items)} items")
                                if items:
                                    print(f"     First item keys: {list(items[0].keys())}")
                                    break
                        except Exception as e:
                            print(f"   {endpoint}: ERROR - {e}")
                
                return True
                
            elif response.status_code == 400:
                error_data = response.json()
                print(f"   ❌ Bad request: {error_data}")
            elif response.status_code == 404:
                print(f"   ⚠️  Collection '{collection}' not found")
            else:
                print(f"   ❌ Unexpected status: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Response text: {response.text[:200]}")
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n❌ Authentication failed with all collections")
    return False


def main():
    """Main function."""
    if len(sys.argv) < 5:
        print("Usage: python test_pocketbase.py <host> <port> <username> <password> [use_ssl]")
        print("Example: python test_pocketbase.py localhost 8090 admin password false")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    username = sys.argv[3]
    password = sys.argv[4]
    use_ssl = len(sys.argv) > 5 and sys.argv[5].lower() in ['true', '1', 'yes']
    
    test_pocketbase_auth(host, port, username, password, use_ssl)


if __name__ == "__main__":
    main()
