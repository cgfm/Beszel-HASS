#!/usr/bin/env python3
"""Analyze Beszel PocketBase data structure."""

import json
import sys

import requests


def analyze_beszel_data(
    host: str, port: int, username: str, password: str, use_ssl: bool = False
):
    """Analyze Beszel data structure."""
    scheme = "https" if use_ssl else "http"
    base_url = f"{scheme}://{host}:{port}"

    print(f"Analyzing Beszel data structure: {base_url}")
    print("=" * 50)

    session = requests.Session()
    session.timeout = 10

    # Authenticate
    auth_data = {"identity": username, "password": password}

    response = session.post(
        f"{base_url}/api/collections/users/auth-with-password", json=auth_data
    )
    if response.status_code != 200:
        print(f"❌ Authentication failed: {response.status_code}")
        return

    auth_result = response.json()
    token = auth_result.get("token")
    headers = {"Authorization": f"Bearer {token}"}

    print("✅ Authentication successful")

    # Get systems
    print("\n1. Analyzing systems data...")
    response = session.get(
        f"{base_url}/api/collections/systems/records", headers=headers
    )
    if response.status_code == 200:
        systems_data = response.json()
        systems = systems_data.get("items", [])
        print(f"Found {len(systems)} systems")

        if systems:
            first_system = systems[0]
            print(f"\nFirst system structure:")
            print(json.dumps(first_system, indent=2))

            # Try to get detailed stats for this system
            system_id = first_system.get("id")
            print(f"\n2. Getting detailed data for system {system_id}...")

            # Get the system record again for latest data
            response = session.get(
                f"{base_url}/api/collections/systems/records/{system_id}",
                headers=headers,
            )
            if response.status_code == 200:
                system_detail = response.json()
                print("System detail:")
                print(json.dumps(system_detail, indent=2))

            # Check if there are other collections with stats
            print(f"\n3. Checking for stats collections...")
            stats_collections = ["stats", "metrics", "system_stats", "logs"]

            for collection in stats_collections:
                try:
                    response = session.get(
                        f"{base_url}/api/collections/{collection}/records",
                        headers=headers,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        print(
                            f"Collection '{collection}': {len(data.get('items', []))} items"
                        )
                        if data.get("items"):
                            print(
                                f"  Sample item: {json.dumps(data['items'][0], indent=4)}"
                            )
                except:
                    pass

    print("\n" + "=" * 50)
    print("Analysis completed!")


def main():
    """Main function."""
    if len(sys.argv) < 5:
        print(
            "Usage: python analyze_beszel.py <host> <port> <username> <password> [use_ssl]"
        )
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    username = sys.argv[3]
    password = sys.argv[4]
    use_ssl = len(sys.argv) > 5 and sys.argv[5].lower() in ["true", "1", "yes"]

    analyze_beszel_data(host, port, username, password, use_ssl)


if __name__ == "__main__":
    main()
