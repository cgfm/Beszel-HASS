"""Data update coordinator for Beszel."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BeszelAPIClient, BeszelAPIError
from .const import CONF_INCLUDE_DOCKER, CONF_SSL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class BeszelDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Beszel data from API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.include_docker = entry.data.get(CONF_INCLUDE_DOCKER, True)
        self._docker_debug_done = False  # Initialize debug flag
        self.api = BeszelAPIClient(
            hass=hass,
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            use_ssl=entry.data.get(CONF_SSL, False),
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            data = await self.api.get_all_stats()
            _LOGGER.debug("Successfully fetched data for %d systems", len(data))

            # Add Docker containers if enabled
            if self.include_docker:
                try:
                    # First time setup: debug available collections
                    if not self._docker_debug_done:
                        try:
                            collections = await self.api.debug_list_collections()
                            _LOGGER.debug(
                                "Available collections for Docker lookup: %s",
                                collections,
                            )
                            self._docker_debug_done = True
                        except (BeszelAPIError, aiohttp.ClientError) as debug_err:
                            _LOGGER.debug("Could not debug collections: %s", debug_err)

                    containers = await self.api.get_docker_containers()
                    if containers:
                        _LOGGER.debug(
                            "Fetched %d Docker container entries", len(containers)
                        )

                        # Group containers by system and container name
                        container_map = {}
                        for container_stats in containers:
                            system_id = container_stats.get("system")
                            container_name = container_stats.get(
                                "n"
                            )  # 'n' is container name

                            # Debug: Log the structure of the first container_stats entry
                            if not container_map:
                                _LOGGER.debug(
                                    "Container stats structure example: %s",
                                    {
                                        k: v
                                        for k, v in container_stats.items()
                                        if k not in ["id", "created", "updated"]
                                    },
                                )

                            if system_id and container_name:
                                # Create unique container ID from system + container name
                                container_key = f"{system_id}_{container_name}"

                                # Use the most recent stats for this container
                                if container_key not in container_map:
                                    container_map[container_key] = {
                                        "system_id": f"docker_{container_key}",
                                        "system_info": {
                                            "id": container_key,
                                            "name": container_name,
                                            "system": system_id,
                                            "created": container_stats.get("created"),
                                            "updated": container_stats.get("updated"),
                                        },
                                        "stats": container_stats,
                                        "type": "docker",
                                    }
                                else:
                                    # Update with newer stats if available
                                    existing_updated = container_map[container_key][
                                        "stats"
                                    ].get("updated", "")
                                    current_updated = container_stats.get("updated", "")
                                    if current_updated > existing_updated:
                                        container_map[container_key][
                                            "stats"
                                        ] = container_stats

                        # Add all containers to data
                        data.update(
                            {
                                f"docker_{key}": container_data
                                for key, container_data in container_map.items()
                            }
                        )
                        _LOGGER.debug(
                            "Created %d Docker container devices", len(container_map)
                        )
                    else:
                        _LOGGER.debug(
                            "No Docker containers found or collections not available"
                        )
                except BeszelAPIError as err:
                    _LOGGER.warning("Failed to fetch Docker containers: %s", err)

            return data
        except BeszelAPIError as err:
            raise UpdateFailed(f"Error communicating with Beszel API: {err}") from err

    @property
    def systems(self) -> list[dict[str, Any]]:
        """Return list of systems."""
        if not self.data:
            return []

        systems = []
        for system_data in self.data.values():
            if "system_info" in system_data:
                systems.append(system_data["system_info"])

        return systems

    def get_system_data(self, system_id: str) -> dict[str, Any] | None:
        """Get data for a specific system."""
        if not self.data:
            return None

        return self.data.get(system_id)

    @property
    def docker_containers(self) -> list[dict[str, Any]]:
        """Return list of Docker containers."""
        if not self.data:
            return []

        containers = []
        for key, container_data in self.data.items():
            if key.startswith("docker_") and container_data.get("type") == "docker":
                containers.append(container_data["system_info"])

        return containers

    def get_docker_data(self, container_id: str) -> dict[str, Any] | None:
        """Get data for a specific Docker container."""
        if not self.data:
            return None

        return self.data.get(f"docker_{container_id}")

    def is_docker_enabled(self) -> bool:
        """Return whether Docker monitoring is enabled."""
        return self.include_docker
