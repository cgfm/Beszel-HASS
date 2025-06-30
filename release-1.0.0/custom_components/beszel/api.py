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


class BeszelAPIError(Exception):
    """Exception for Beszel API errors."""
