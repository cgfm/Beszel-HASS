"""API client for Beszel (PocketBase)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)


class BeszelAPIClient:
    """API client for Beszel using PocketBase."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        username: str,
        password: str,
        use_ssl: bool = False,
    ) -> None:
        """Initialize the API client."""
        self._hass = hass
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._use_ssl = use_ssl
        self._session = async_get_clientsession(hass)
        self._auth_token: str | None = None

        scheme = "https" if use_ssl else "http"
        self._base_url = f"{scheme}://{host}:{port}"

    async def authenticate(self) -> bool:
        """Authenticate with the Beszel PocketBase API."""
        try:
            auth_data = {"identity": self._username, "password": self._password}

            async with self._session.post(
                f"{self._base_url}/api/collections/users/auth-with-password",
                json=auth_data,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._auth_token = data.get("token")
                    return True

                _LOGGER.error("Authentication failed with status %s", response.status)
                return False

        except aiohttp.ClientError as err:
            _LOGGER.error("Error during authentication: %s", err)
            return False

    async def get_systems(self) -> list[dict[str, Any]]:
        """Get list of monitored systems from PocketBase."""
        if not self._auth_token:
            if not await self.authenticate():
                raise BeszelAPIError("Authentication failed")

        try:
            headers = {"Authorization": f"Bearer {self._auth_token}"}
            async with self._session.get(
                f"{self._base_url}/api/collections/systems/records",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 401:
                    # Token might be expired, try to re-authenticate
                    if await self.authenticate():
                        headers = {"Authorization": f"Bearer {self._auth_token}"}
                        async with self._session.get(
                            f"{self._base_url}/api/collections/systems/records",
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as retry_response:
                            if retry_response.status == 200:
                                data = await retry_response.json()
                                return data.get("items", [])
                    raise BeszelAPIError("Authentication failed")
                if response.status == 200:
                    data = await response.json()
                    return data.get("items", [])

                raise BeszelAPIError(
                    f"API request failed with status {response.status}"
                )

        except aiohttp.ClientError as err:
            _LOGGER.error("Error getting systems: %s", err)
            raise BeszelAPIError(f"Network error: {err}") from err

    async def get_system_id_to_name_mapping(self) -> dict[str, str]:
        """Get a mapping of system IDs to system names."""
        try:
            systems = await self.get_systems()
            mapping = {}
            for system in systems:
                system_id = system.get("id")
                system_name = system.get("name", "Unknown")
                if system_id:
                    mapping[system_id] = system_name

            _LOGGER.debug("System ID to name mapping: %s", mapping)
            return mapping
        except BeszelAPIError as err:
            _LOGGER.error("Error getting system mapping: %s", err)
            return {}

    async def get_system_stats(self, system_id: str) -> dict[str, Any]:
        """Get stats for a specific system from PocketBase."""
        if not self._auth_token:
            if not await self.authenticate():
                raise BeszelAPIError("Authentication failed")

        try:
            headers = {"Authorization": f"Bearer {self._auth_token}"}
            # Get the system record which should contain current stats
            url = f"{self._base_url}/api/collections/systems/records/{system_id}"

            async with self._session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 401:
                    # Token might be expired, try to re-authenticate
                    if await self.authenticate():
                        headers = {"Authorization": f"Bearer {self._auth_token}"}
                        async with self._session.get(
                            url,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as retry_response:
                            if retry_response.status == 200:
                                return await retry_response.json()
                    raise BeszelAPIError("Authentication failed")
                if response.status == 200:
                    return await response.json()

                raise BeszelAPIError(
                    f"API request failed with status {response.status}"
                )

        except aiohttp.ClientError as err:
            _LOGGER.error("Error getting system stats for %s: %s", system_id, err)
            raise BeszelAPIError(f"Network error: {err}") from err

    async def get_all_stats(self) -> dict[str, Any]:
        """Get stats for all systems."""
        systems = await self.get_systems()
        all_stats = {}

        # Get stats for each system
        tasks = []
        for system in systems:
            system_id = system.get("id")
            if system_id:
                tasks.append(self._get_system_stats_with_id(system_id, system))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, dict) and "system_id" in result:
                    all_stats[result["system_id"]] = result
                elif isinstance(result, Exception):
                    _LOGGER.error("Error getting stats: %s", result)

        return all_stats

    async def _get_system_stats_with_id(
        self, system_id: str, system_info: dict
    ) -> dict[str, Any]:
        """Get stats for a system and include system info."""
        try:
            stats = await self.get_system_stats(system_id)
            return {"system_id": system_id, "system_info": system_info, "stats": stats}
        except BeszelAPIError as err:
            _LOGGER.error("Error getting stats for system %s: %s", system_id, err)
            return {
                "system_id": system_id,
                "system_info": system_info,
                "stats": None,
                "error": str(err),
            }

    async def get_docker_containers(self) -> list[dict[str, Any]]:
        """Get list of Docker containers from PocketBase using container_stats collection."""
        if not self._auth_token:
            if not await self.authenticate():
                raise BeszelAPIError("Authentication failed")

        try:
            headers = {"Authorization": f"Bearer {self._auth_token}"}

            # Use the known container_stats endpoint
            url = f"{self._base_url}/api/collections/container_stats/records"

            # Get recent container stats, sorted by creation time
            params = {
                "sort": "-created",  # Get most recent first
                "perPage": 100,  # Reasonable limit for container stats
                "expand": "system",  # Expand system relation if available
            }

            _LOGGER.debug("Fetching container stats from: %s", url)

            async with self._session.get(
                url,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 401:
                    # Token might be expired, try to re-authenticate
                    if await self.authenticate():
                        headers = {"Authorization": f"Bearer {self._auth_token}"}
                        async with self._session.get(
                            url,
                            headers=headers,
                            params=params,
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as retry_response:
                            if retry_response.status == 200:
                                data = await retry_response.json()
                                return (
                                    await self._extract_containers_from_container_stats(
                                        data
                                    )
                                )
                    raise BeszelAPIError("Authentication failed after retry")

                elif response.status == 200:
                    data = await response.json()
                    containers = await self._extract_containers_from_container_stats(
                        data
                    )
                    _LOGGER.info(
                        "Found %d containers from container_stats collection",
                        len(containers),
                    )
                    return containers

                elif response.status == 404:
                    _LOGGER.warning(
                        "container_stats collection not found - trying fallback methods"
                    )
                    return await self._get_containers_fallback()

                else:
                    _LOGGER.error(
                        "Failed to fetch container stats: HTTP %d", response.status
                    )
                    # Try fallback methods
                    return await self._get_containers_fallback()

        except aiohttp.ClientError as err:
            _LOGGER.error("Network error while fetching containers: %s", err)
            raise BeszelAPIError(f"Network error: {err}") from err

    async def _extract_containers_from_container_stats(
        self, data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extract container information from container_stats collection with correct data structure."""
        containers = []
        items = data.get("items", [])

        if not items:
            _LOGGER.warning("No items found in container_stats collection")
            return containers

        _LOGGER.debug("Processing %d container_stats items", len(items))

        # Get system ID to name mapping for proper naming
        system_id_to_name = await self.get_system_id_to_name_mapping()
        _LOGGER.debug("System mapping available for %d systems", len(system_id_to_name))

        # Group by system to get only the latest stats for each system
        systems_latest = {}

        # First pass: find the latest record for each system
        for item in items:
            system_id = item.get("system")
            created = item.get("created")

            if not system_id or not created:
                continue

            if (
                system_id not in systems_latest
                or created > systems_latest[system_id]["created"]
            ):
                systems_latest[system_id] = item

        _LOGGER.info("Found latest stats for %d systems", len(systems_latest))

        # Second pass: extract containers from latest records
        for system_id, item in systems_latest.items():
            try:
                # Get system name for proper container naming
                system_name = system_id_to_name.get(system_id, f"Unknown-{system_id}")

                stats_data = item.get("stats", [])

                # Debug: Log the raw stats_data structure
                _LOGGER.debug(
                    "Raw stats_data for system %s: type=%s, content=%s",
                    system_id,
                    type(stats_data).__name__,
                    str(stats_data)[:200],
                )

                # NEW DEBUG: More detailed logging for troubleshooting
                if isinstance(stats_data, list):
                    _LOGGER.debug(
                        "DEBUG: stats_data is list with %d items for system %s",
                        len(stats_data),
                        system_id,
                    )
                    if stats_data:
                        first_item = stats_data[0]
                        _LOGGER.debug(
                            "DEBUG: First item type=%s, keys=%s",
                            type(first_item).__name__,
                            (
                                list(first_item.keys())
                                if isinstance(first_item, dict)
                                else "N/A"
                            ),
                        )
                        if isinstance(first_item, dict):
                            _LOGGER.debug("DEBUG: First item content: %s", first_item)
                            # Check specifically for container field 'n'
                            if "n" in first_item:
                                _LOGGER.debug(
                                    "DEBUG: Container name field 'n' found: %s",
                                    first_item["n"],
                                )
                            else:
                                _LOGGER.warning(
                                    "DEBUG: Container name field 'n' missing in first item keys: %s",
                                    list(first_item.keys()),
                                )
                else:
                    _LOGGER.debug(
                        "DEBUG: stats_data is not a list: type=%s",
                        type(stats_data).__name__,
                    )

                # Check if stats_data is a string and needs parsing (old format)
                if isinstance(stats_data, str):
                    import json

                    try:
                        stats_data = json.loads(stats_data)
                        _LOGGER.debug(
                            "Parsed stats_data from JSON string for system %s: type=%s, length=%s",
                            system_id,
                            type(stats_data).__name__,
                            (
                                len(stats_data)
                                if isinstance(stats_data, (list, dict))
                                else "N/A"
                            ),
                        )
                    except json.JSONDecodeError:
                        _LOGGER.warning(
                            "Failed to parse stats JSON for system %s", system_id
                        )
                        continue
                elif isinstance(stats_data, list):
                    # Stats data is already a list (new format)
                    _LOGGER.debug(
                        "Stats_data is already a list for system %s with %d items",
                        system_id,
                        len(stats_data),
                    )

                # Extract containers from stats array
                if isinstance(stats_data, list):
                    _LOGGER.debug(
                        "Processing %d items in stats_data list for system %s",
                        len(stats_data),
                        system_id,
                    )

                    for i, container_data in enumerate(stats_data):
                        _LOGGER.debug(
                            "Container %d data for system %s: type=%s, keys=%s",
                            i,
                            system_id,
                            type(container_data).__name__,
                            (
                                list(container_data.keys())
                                if isinstance(container_data, dict)
                                else "N/A"
                            ),
                        )

                        # Check if this is a container dict with the expected structure
                        if isinstance(container_data, dict) and "n" in container_data:
                            container_name = container_data["n"]
                            # Create unique container key with system name for better identification
                            container_key = f"{system_name}_{container_name}"

                            # Convert abbreviated fields to full names with type conversion
                            container_info = {
                                "id": container_key,
                                "name": container_name,
                                "system": system_id,
                                "system_name": system_name,  # Add system name for better display
                                "created": item.get("created"),
                                "updated": item.get("updated"),
                                "type": item.get("type", "1m"),
                                "stats": {
                                    "cpu": (
                                        float(container_data.get("c", 0))
                                        if container_data.get("c") is not None
                                        else 0.0
                                    ),
                                    "memory": (
                                        int(container_data.get("m", 0))
                                        if container_data.get("m") is not None
                                        else 0
                                    ),
                                    "network_sent": (
                                        int(container_data.get("ns", 0))
                                        if container_data.get("ns") is not None
                                        else 0
                                    ),
                                    "network_received": (
                                        int(container_data.get("nr", 0))
                                        if container_data.get("nr") is not None
                                        else 0
                                    ),
                                    "raw": container_data,  # Keep original data for reference
                                },
                            }

                            containers.append(container_info)
                            _LOGGER.debug(
                                "Found container: %s on system %s (%s) - CPU: %s%%, Memory: %s, Net S/R: %s/%s",
                                container_name,
                                system_name,
                                system_id,
                                container_data.get("c"),
                                container_data.get("m"),
                                container_data.get("ns"),
                                container_data.get("nr"),
                            )
                        else:
                            _LOGGER.debug(
                                "Skipping non-container data at index %d for system %s: %s",
                                i,
                                system_id,
                                container_data,
                            )

                elif isinstance(stats_data, dict):
                    # Fallback: sometimes stats might be a dict instead of array
                    _LOGGER.debug(
                        "Stats is dict instead of array for system %s (%s), keys: %s",
                        system_id,
                        system_name,
                        list(stats_data.keys()),
                    )

            except Exception as err:
                system_name = system_id_to_name.get(system_id, f"Unknown-{system_id}")
                _LOGGER.warning(
                    "Error processing container_stats for system %s (%s): %s",
                    system_id,
                    system_name,
                    err,
                )
                continue

        # Log summary
        if containers:
            _LOGGER.info(
                "Successfully extracted %d containers from %d systems",
                len(containers),
                len(systems_latest),
            )

            # Log container details for debugging with system names
            for container in containers[:5]:  # Log first 5 for debugging
                _LOGGER.info(
                    "Container found: %s on %s (CPU: %s%%, Memory: %s MB, Net S/R: %s/%s KB)",
                    container["name"],
                    container.get("system_name", container["system"]),
                    container["stats"]["cpu"],
                    container["stats"]["memory"],
                    container["stats"]["network_sent"],
                    container["stats"]["network_received"],
                )
        else:
            _LOGGER.warning(
                "No containers could be extracted from container_stats data"
            )
            # Log sample data structure for debugging
            if systems_latest:
                sample_system = next(iter(systems_latest.values()))
                sample_stats = sample_system.get("stats")
                _LOGGER.warning(
                    "Sample stats structure - Type: %s, Length: %s, Content: %s",
                    type(sample_stats).__name__,
                    (
                        len(sample_stats)
                        if isinstance(sample_stats, (list, dict))
                        else "N/A"
                    ),
                    str(sample_stats)[:300] if sample_stats else "None",
                )

        return containers

    async def _get_containers_fallback(self) -> list[dict[str, Any]]:
        """Fallback method to get containers from other collections."""
        _LOGGER.info("Using fallback method to find containers")

        # Try other collection names as fallback
        collection_names = [
            "stats",
            "containers",
            "docker",
            "docker_stats",
            "system_stats",
        ]

        all_containers = []

        for collection_name in collection_names:
            try:
                headers = {"Authorization": f"Bearer {self._auth_token}"}
                params = {"sort": "-created", "perPage": 100}

                url = f"{self._base_url}/api/collections/{collection_name}/records"

                async with self._session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        containers = await self._extract_containers_from_data(
                            data, collection_name
                        )
                        if containers:
                            all_containers.extend(containers)
                            _LOGGER.info(
                                "Found %d containers in fallback collection '%s'",
                                len(containers),
                                collection_name,
                            )
                    elif response.status == 404:
                        _LOGGER.debug("Collection '%s' not found", collection_name)

            except Exception as err:
                _LOGGER.debug(
                    "Error accessing collection '%s': %s", collection_name, err
                )
                continue

        return all_containers

    async def _extract_containers_from_data(
        self, data: dict[str, Any], collection_name: str
    ) -> list[dict[str, Any]]:
        """Extract container information from PocketBase data."""
        containers = []
        items = data.get("items", [])

        if not items:
            return containers

        # Log structure of first item for debugging
        if items:
            first_item = items[0]
            _LOGGER.debug(
                "Sample item from '%s': keys=%s",
                collection_name,
                list(first_item.keys()),
            )

        for item in items:
            # Method 1: Look for direct container data structure
            if "containers" in item:
                container_data = item["containers"]
                if isinstance(container_data, list):
                    for container in container_data:
                        container_info = {
                            "id": f"{item.get('id', 'unknown')}_{container.get('name', 'unknown')}",
                            "name": container.get("name"),
                            "system": item.get("system"),
                            "created": item.get("created"),
                            "stats": container,
                        }
                        containers.append(container_info)
                elif isinstance(container_data, dict):
                    # Single container or containers as object
                    for name, stats in container_data.items():
                        container_info = {
                            "id": f"{item.get('id', 'unknown')}_{name}",
                            "name": name,
                            "system": item.get("system"),
                            "created": item.get("created"),
                            "stats": stats,
                        }
                        containers.append(container_info)

            # Method 2: Look for fields that indicate this is container data
            elif "container_name" in item or "n" in item:  # 'n' might be container name
                container_info = {
                    "id": item.get("id"),
                    "name": item.get("container_name") or item.get("n"),
                    "system": item.get("system"),
                    "created": item.get("created"),
                    "stats": item,
                }
                containers.append(container_info)

            # Method 3: Look for specific docker/container fields
            elif any(key.startswith(("docker_", "container_")) for key in item.keys()):
                # This looks like container stats
                container_info = {
                    "id": item.get("id"),
                    "name": item.get("name", "unknown"),
                    "system": item.get("system"),
                    "created": item.get("created"),
                    "stats": item,
                }
                containers.append(container_info)

        return containers

    async def get_docker_stats(self, container_id: str) -> dict[str, Any]:
        """Get stats for a specific Docker container from PocketBase."""
        if not self._auth_token:
            if not await self.authenticate():
                raise BeszelAPIError("Authentication failed")

        try:
            headers = {"Authorization": f"Bearer {self._auth_token}"}
            # Get the container record which should contain current stats
            url = f"{self._base_url}/api/collections/docker/records/{container_id}"

            async with self._session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 401:
                    # Token might be expired, try to re-authenticate
                    if await self.authenticate():
                        headers = {"Authorization": f"Bearer {self._auth_token}"}
                        async with self._session.get(
                            url,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as retry_response:
                            if retry_response.status == 200:
                                return await retry_response.json()
                    raise BeszelAPIError("Authentication failed")
                if response.status == 200:
                    return await response.json()

                raise BeszelAPIError(
                    f"API request failed with status {response.status}"
                )

        except aiohttp.ClientError as err:
            _LOGGER.error("Error getting docker stats for %s: %s", container_id, err)
            raise BeszelAPIError(f"Network error: {err}") from err

    async def debug_list_collections(self) -> list[dict[str, Any]]:
        """Debug method to list all available collections in PocketBase."""
        if not self._auth_token:
            if not await self.authenticate():
                raise BeszelAPIError("Authentication failed")

        try:
            headers = {"Authorization": f"Bearer {self._auth_token}"}

            # Try to list collections via admin API
            async with self._session.get(
                f"{self._base_url}/api/collections",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug(
                        "Available collections: %s", [col.get("name") for col in data]
                    )
                    return data
                _LOGGER.debug("Could not list collections, status: %s", response.status)

            # Alternative: try some common collection names
            common_collections = [
                "container_stats",
                "containers",
                "docker_stats",
                "docker_containers",
            ]
            found_collections = []

            for collection_name in common_collections:
                try:
                    async with self._session.get(
                        f"{self._base_url}/api/collections/{collection_name}/records",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            found_collections.append(
                                {
                                    "name": collection_name,
                                    "count": len(data.get("items", [])),
                                }
                            )
                            _LOGGER.debug(
                                "Found collection '%s' with %d items",
                                collection_name,
                                len(data.get("items", [])),
                            )
                        elif response.status == 404:
                            _LOGGER.debug("Collection '%s' not found", collection_name)
                except Exception as exc:
                    _LOGGER.debug(
                        "Error checking collection '%s': %s", collection_name, exc
                    )

            return found_collections

        except aiohttp.ClientError as err:
            _LOGGER.error("Error listing collections: %s", err)
            raise BeszelAPIError(f"Network error: {err}") from err


class BeszelAPIError(Exception):
    """Exception for Beszel API errors."""
