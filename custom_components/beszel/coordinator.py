"""Data update coordinator for Beszel."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

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
                    containers = await self.api.get_docker_containers()
                    if containers:
                        _LOGGER.debug("Fetched %d Docker containers", len(containers))
                        # Add containers to data with docker_ prefix
                        for container in containers:
                            container_id = container.get("id")
                            if container_id:
                                data[f"docker_{container_id}"] = {
                                    "system_id": f"docker_{container_id}",
                                    "system_info": container,
                                    "stats": container,
                                    "type": "docker",
                                }
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
