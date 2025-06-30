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
        """Get list of Docker containers from PocketBase."""
        if not self._auth_token:
            if not await self.authenticate():
                raise BeszelAPIError("Authentication failed")

        # Try different possible collection names for container data
        collection_names = ["container_stats", "containers", "docker", "docker_stats"]

        for collection_name in collection_names:
            try:
                headers = {"Authorization": f"Bearer {self._auth_token}"}
                async with self._session.get(
                    f"{self._base_url}/api/collections/{collection_name}/records",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 401:
                        # Token might be expired, try to re-authenticate
                        if await self.authenticate():
                            headers = {"Authorization": f"Bearer {self._auth_token}"}
                            async with self._session.get(
                                f"{self._base_url}/api/collections/{collection_name}/records",
                                headers=headers,
                                timeout=aiohttp.ClientTimeout(total=10),
                            ) as retry_response:
                                if retry_response.status == 200:
                                    data = await retry_response.json()
                                    _LOGGER.debug(
                                        "Found containers in '%s': %d items",
                                        collection_name,
                                        len(data.get("items", [])),
                                    )
                                    return data.get("items", [])
                        raise BeszelAPIError("Authentication failed")
                    if response.status == 200:
                        data = await response.json()
                        _LOGGER.debug(
                            "Found containers in '%s': %d items",
                            collection_name,
                            len(data.get("items", [])),
                        )
                        return data.get("items", [])
                    if response.status == 404:
                        _LOGGER.debug(
                            "Collection '%s' not found, trying next...", collection_name
                        )
                        continue
                    _LOGGER.debug(
                        "Collection '%s' returned status %s",
                        collection_name,
                        response.status,
                    )
                    continue

            except aiohttp.ClientError as err:
                _LOGGER.debug(
                    "Error accessing collection '%s': %s", collection_name, err
                )
                continue

        # If we get here, no collection was found
        _LOGGER.debug(
            "No Docker container collections found - tried: %s", collection_names
        )
        return []

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
