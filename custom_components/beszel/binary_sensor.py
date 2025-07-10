"""Support for Beszel binary sensors."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BeszelDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Beszel binary sensors based on a config entry."""
    coordinator: BeszelDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Create status sensors for each system
    for system_data in coordinator.data.values():
        if "system_info" in system_data:
            data_type = system_data.get("type", "system")
            system_info = system_data["system_info"]
            system_id = system_info.get("id")

            if data_type == "docker":
                # Handle Docker containers
                if coordinator.is_docker_enabled():
                    container_name = system_info.get("name", f"Container {system_id}")
                    system_name = system_info.get("system_name", "Unknown System")

                    # Create display name with system context
                    display_name = f"{container_name} ({system_name})"

                    entities.append(
                        BeszelDockerBinarySensor(
                            coordinator=coordinator,
                            container_id=system_id,
                            container_name=display_name,
                        )
                    )
            else:
                # Handle regular systems
                system_name = system_info.get("name", f"System {system_id}")
                entities.append(
                    BeszelBinarySensor(
                        coordinator=coordinator,
                        system_id=system_id,
                        system_name=system_name,
                    )
                )

    async_add_entities(entities)


class BeszelBinarySensor(
    CoordinatorEntity[BeszelDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of a Beszel system status binary sensor."""

    def __init__(
        self,
        coordinator: BeszelDataUpdateCoordinator,
        system_id: str,
        system_name: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)

        self._system_id = system_id
        self._system_name = system_name

        self._attr_name = f"{system_name} Status"
        self._attr_unique_id = f"{system_id}_status_v4"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, system_id)},
            "name": system_name,
            "manufacturer": "Beszel",
            "model": "Server Monitor",
        }

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        system_data = self.coordinator.get_system_data(self._system_id)
        if not system_data:
            return False

        system_info = system_data.get("system_info", {})
        status = system_info.get("status", "").lower()

        # System is "on" if status is "up"
        return status == "up"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.get_system_data(self._system_id) is not None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        system_data = self.coordinator.get_system_data(self._system_id)
        if not system_data:
            return None

        system_info = system_data.get("system_info", {})

        return {
            "system_id": self._system_id,
            "system_name": system_info.get("name"),
            "host": system_info.get("host"),
            "port": system_info.get("port"),
            "status": system_info.get("status"),
            "last_updated": system_info.get("updated"),
        }


class BeszelDockerBinarySensor(
    CoordinatorEntity[BeszelDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of a Beszel Docker container status binary sensor."""

    def __init__(
        self,
        coordinator: BeszelDataUpdateCoordinator,
        container_id: str,
        container_name: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)

        self._container_id = container_id
        self._container_name = container_name

        # Create unique ID (v4 to force recreation and match sensor format)
        self._attr_unique_id = f"docker_{container_id}_status_v4"

        # Set entity name
        self._attr_name = f"Docker {container_name} Status"

        # Set device class
        self._attr_device_class = BinarySensorDeviceClass.RUNNING

        # Set device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"docker_{container_id}")},
            "name": f"Docker: {container_name}",
            "manufacturer": "Docker",
            "model": "Container",
            "configuration_url": None,
        }

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        container_data = self.coordinator.get_docker_data(self._container_id)
        if not container_data:
            _LOGGER.debug(
                "DEBUG: Binary sensor %s - no container data", self._container_id
            )
            return False

        container_info = container_data.get("system_info", {})
        status = container_info.get("status", "").lower()

        _LOGGER.debug(
            "DEBUG: Binary sensor %s - status='%s'", self._container_id, status
        )

        # If we have container data from the API, the container is running
        # The API only returns containers that exist and are active
        _LOGGER.debug(
            "DEBUG: Binary sensor %s - container exists, setting to ON",
            self._container_id,
        )

        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        container_data = self.coordinator.get_docker_data(self._container_id)
        if not container_data:
            return {}

        container_info = container_data.get("system_info", {})

        return {
            "container_id": self._container_id,
            "container_name": container_info.get("name"),
            "image": container_info.get("image"),
            "status": container_info.get("status"),
            "created": container_info.get("created"),
            "updated": container_info.get("updated"),
            "ports": container_info.get("ports"),
            "labels": container_info.get("labels"),
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        container_data = self.coordinator.get_docker_data(self._container_id)
        is_available = container_data is not None

        _LOGGER.debug(
            "DEBUG: Binary sensor %s available check: %s",
            self._container_id,
            is_available,
        )

        return is_available
