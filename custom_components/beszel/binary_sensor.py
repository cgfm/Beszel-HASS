"""Support for Beszel binary sensors."""

from __future__ import annotations

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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Beszel binary sensor based on a config entry."""
    coordinator: BeszelDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Create binary sensors for each system
    for system_data in coordinator.data.values():
        if "system_info" in system_data:
            data_type = system_data.get("type", "system")
            system_info = system_data["system_info"]
            system_id = system_info.get("id")

            if data_type == "docker":
                # Handle Docker containers
                if coordinator.is_docker_enabled():
                    container_name = system_info.get("name", f"Container {system_id}")
                    entities.append(
                        BeszelDockerBinarySensor(
                            coordinator=coordinator,
                            container_id=system_id,
                            container_name=container_name,
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
    """Representation of a Beszel binary sensor for system status."""

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
        self._attr_unique_id = f"{system_id}_status"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_icon = "mdi:server"

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, system_id)},
            "name": system_name,
            "manufacturer": "Beszel",
            "model": "Server Monitor",
            "via_device": (DOMAIN, coordinator.entry.entry_id),
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if the system is online."""
        system_data = self.coordinator.get_system_data(self._system_id)
        if not system_data:
            return False

        # Check system status from PocketBase
        if "system_info" in system_data:
            system_info = system_data["system_info"]
            status = system_info.get("status")
            return status == "up"

        return None

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

        attributes = {}

        # Add system info
        if "system_info" in system_data:
            system_info = system_data["system_info"]
            attributes["system_id"] = system_info.get("id")
            attributes["system_name"] = system_info.get("name")
            attributes["os"] = system_info.get("os")
            attributes["arch"] = system_info.get("arch")
            attributes["version"] = system_info.get("version")

        # Add error info if present
        if "error" in system_data:
            attributes["last_error"] = system_data["error"]

        # Add last update time if stats are available
        if "stats" in system_data and system_data["stats"]:
            stats = system_data["stats"]
            if "timestamp" in stats:
                attributes["last_update"] = stats["timestamp"]

        return attributes if attributes else None


class BeszelDockerBinarySensor(
    CoordinatorEntity[BeszelDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of a Beszel Docker container status sensor."""

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

        # Create unique ID
        self._attr_unique_id = f"docker_{container_id}_status"

        # Set entity name
        self._attr_name = f"Docker {container_name} Status"

        # Set device info (same as sensors)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"docker_{container_id}")},
            "name": f"Docker: {container_name}",
            "manufacturer": "Docker",
            "model": "Container",
            "configuration_url": None,
            "via_device": (DOMAIN, coordinator.entry.entry_id),
        }

        # Set binary sensor attributes
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_icon = "mdi:docker"

    @property
    def is_on(self) -> bool:
        """Return true if the container is running."""
        container_data = self.coordinator.get_docker_data(self._container_id)
        if not container_data:
            return False

        container_info = container_data.get("system_info", {})
        status = container_info.get("status", "").lower()

        # Container is "on" (running) if status indicates it's running
        return status in ["running", "up"]

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
        return self.coordinator.get_docker_data(self._container_id) is not None
