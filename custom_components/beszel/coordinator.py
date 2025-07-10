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
                        _LOGGER.info(
                            "Fetched %d Docker container entries", len(containers)
                        )

                        # Group containers by system and container name
                        container_map = {}
                        for container_data in containers:
                            container_name = container_data.get("name")
                            system_id = container_data.get("system")

                            # Debug: Log the structure of the first container entry
                            if not container_map:
                                _LOGGER.debug(
                                    "Container data structure example: %s",
                                    {
                                        k: (
                                            str(v)[:100] + "..."
                                            if len(str(v)) > 100
                                            else v
                                        )
                                        for k, v in container_data.items()
                                        if k not in ["id", "created", "updated"]
                                    },
                                )

                            if container_name:
                                # Create unique container ID
                                container_key = (
                                    f"{system_id}_{container_name}"
                                    if system_id
                                    else container_name
                                )

                                # Get system name for better identification
                                system_name = container_data.get(
                                    "system_name", f"System-{system_id}"
                                )

                                # Use the most recent stats for this container
                                if container_key not in container_map:
                                    container_map[container_key] = {
                                        "system_id": f"docker_{container_key}",
                                        "system_info": {
                                            "id": container_data.get(
                                                "id", container_key
                                            ),
                                            "name": container_name,
                                            "system": system_id,
                                            "system_name": system_name,  # Add system name to container info
                                            "created": container_data.get("created"),
                                            "updated": container_data.get("updated"),
                                        },
                                        "stats": container_data.get(
                                            "stats", container_data
                                        ),
                                        "type": "docker",
                                    }
                                else:
                                    # Update with newer stats if available
                                    existing_updated = container_map[container_key][
                                        "stats"
                                    ].get("updated", "")
                                    current_updated = container_data.get("updated", "")
                                    if current_updated > existing_updated:
                                        container_map[container_key]["stats"] = (
                                            container_data.get("stats", container_data)
                                        )
                                        # Also update system name if newer data has it
                                        if container_data.get("system_name"):
                                            container_map[container_key]["system_info"][
                                                "system_name"
                                            ] = container_data.get("system_name")

                        # Add all containers to data
                        for container_key, container_info in container_map.items():
                            data[container_info["system_id"]] = container_info

                        _LOGGER.info(
                            "Successfully processed %d unique Docker containers",
                            len(container_map),
                        )
                    else:
                        _LOGGER.warning("No Docker containers found")

                except (BeszelAPIError, aiohttp.ClientError) as docker_err:
                    _LOGGER.error("Error fetching Docker containers: %s", docker_err)
                    # Don't fail the entire update if Docker fails
                    pass

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

        # Log all available keys for debugging
        _LOGGER.debug("DEBUG: Available data keys: %s", list(self.data.keys()))
        _LOGGER.debug("DEBUG: Looking for container_id: %s", container_id)

        # Try direct lookup first (for newer format)
        direct_result = self.data.get(container_id)
        if direct_result:
            _LOGGER.debug("DEBUG: Found container via direct lookup: %s", container_id)
            return direct_result

        # Try with docker_ prefix
        prefixed_result = self.data.get(f"docker_{container_id}")
        if prefixed_result:
            _LOGGER.debug("DEBUG: Found container via docker_ prefix: %s", container_id)
            return prefixed_result

        # Search through all data for matching container
        for key, data in self.data.items():
            if (
                data.get("type") == "docker"
                and data.get("system_info", {}).get("id") == container_id
            ):
                _LOGGER.debug(
                    "DEBUG: Found container via system_info search: %s (key: %s)",
                    container_id,
                    key,
                )
                return data

        _LOGGER.warning("DEBUG: Container not found: %s", container_id)
        return None

    def is_docker_enabled(self) -> bool:
        """Return whether Docker monitoring is enabled."""
        return self.include_docker
