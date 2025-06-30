"""Support for Beszel sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOCKER_SENSOR_TYPES, DOMAIN, SENSOR_TYPES
from .coordinator import BeszelDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Beszel sensor based on a config entry."""
    coordinator: BeszelDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Create sensors for each system
    for system_data in coordinator.data.values():
        if "system_info" in system_data and "stats" in system_data:
            data_type = system_data.get("type", "system")
            system_info = system_data["system_info"]
            system_id = system_info.get("id")

            if data_type == "docker":
                # Handle Docker containers
                if coordinator.is_docker_enabled():
                    container_name = system_info.get("name", f"Container {system_id}")
                    for sensor_type, sensor_config in DOCKER_SENSOR_TYPES.items():
                        entities.append(
                            BeszelDockerSensor(
                                coordinator=coordinator,
                                container_id=system_id,
                                container_name=container_name,
                                sensor_type=sensor_type,
                                sensor_config=sensor_config,
                            )
                        )
            else:
                # Handle regular systems
                system_name = system_info.get("name", f"System {system_id}")
                for sensor_type, sensor_config in SENSOR_TYPES.items():
                    entities.append(
                        BeszelSensor(
                            coordinator=coordinator,
                            system_id=system_id,
                            system_name=system_name,
                            sensor_type=sensor_type,
                            sensor_config=sensor_config,
                        )
                    )

    async_add_entities(entities)


class BeszelSensor(CoordinatorEntity[BeszelDataUpdateCoordinator], SensorEntity):
    """Representation of a Beszel sensor."""

    def __init__(
        self,
        coordinator: BeszelDataUpdateCoordinator,
        system_id: str,
        system_name: str,
        sensor_type: str,
        sensor_config: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._system_id = system_id
        self._system_name = system_name
        self._sensor_type = sensor_type
        self._sensor_config = sensor_config

        self._attr_name = f"{system_name} {sensor_config['name']}"
        self._attr_unique_id = f"{system_id}_{sensor_type}"
        self._attr_native_unit_of_measurement = sensor_config.get("unit")
        self._attr_icon = sensor_config.get("icon")
        self._attr_device_class = sensor_config.get("device_class")
        self._attr_state_class = SensorStateClass.MEASUREMENT

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, system_id)},
            "name": system_name,
            "manufacturer": "Beszel",
            "model": "Server Monitor",
            "via_device": (DOMAIN, coordinator.entry.entry_id),
        }

    @property
    def native_value(self) -> float | int | str | None:
        """Return the state of the sensor."""
        system_data = self.coordinator.get_system_data(self._system_id)
        if not system_data or "system_info" not in system_data:
            return None

        system_info = system_data["system_info"]
        info = system_info.get("info", {})

        if not info:
            return None

        # Get the value based on the info_key mapping
        info_key = self._sensor_config.get("info_key")
        if info_key:
            value = info.get(info_key)
            if value is not None:
                # Convert to appropriate type and precision
                if isinstance(value, (int, float)):
                    return round(float(value), 2)
                return value

        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.get_system_data(self._system_id) is not None
            and self.coordinator.get_system_data(self._system_id)
            .get("system_info", {})
            .get("status")
            == "up"
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
            attributes["host"] = system_info.get("host")
            attributes["port"] = system_info.get("port")
            attributes["status"] = system_info.get("status")
            attributes["last_updated"] = system_info.get("updated")

            # Add detailed info from the info field
            info = system_info.get("info", {})
            if info:
                attributes["hostname"] = info.get("h")  # hostname
                attributes["kernel"] = info.get("k")  # kernel version
                attributes["cpu_cores"] = info.get("c")  # cpu cores
                attributes["cpu_threads"] = info.get("t")  # cpu threads
                attributes["cpu_model"] = info.get("m")  # cpu model
                attributes["agent_version"] = info.get("v")  # beszel agent version
                attributes["os_type"] = info.get("os")  # os type

        return attributes if attributes else None


class BeszelDockerSensor(CoordinatorEntity[BeszelDataUpdateCoordinator], SensorEntity):
    """Representation of a Beszel Docker container sensor."""

    def __init__(
        self,
        coordinator: BeszelDataUpdateCoordinator,
        container_id: str,
        container_name: str,
        sensor_type: str,
        sensor_config: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._container_id = container_id
        self._container_name = container_name
        self._sensor_type = sensor_type
        self._sensor_config = sensor_config

        # Create unique ID
        self._attr_unique_id = f"docker_{container_id}_{sensor_type}"

        # Set entity name
        self._attr_name = f"Docker {container_name} {sensor_config['name']}"

        # Set device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"docker_{container_id}")},
            "name": f"Docker: {container_name}",
            "manufacturer": "Docker",
            "model": "Container",
            "configuration_url": None,
            "via_device": (DOMAIN, coordinator.entry.entry_id),
        }

        # Set sensor attributes
        self._attr_native_unit_of_measurement = sensor_config.get("unit")
        self._attr_device_class = sensor_config.get("device_class")
        self._attr_state_class = sensor_config.get(
            "state_class", SensorStateClass.MEASUREMENT
        )
        self._attr_icon = sensor_config.get("icon")

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        container_data = self.coordinator.get_docker_data(self._container_id)
        if not container_data:
            return None

        stats = container_data.get("stats", {})
        if not stats:
            return None

        # Extract values based on sensor type
        if self._sensor_type == "docker_cpu":
            return stats.get("cpu_percent")
        elif self._sensor_type == "docker_memory":
            return stats.get("memory_percent")
        elif self._sensor_type == "docker_memory_bytes":
            return stats.get("memory_usage")
        elif self._sensor_type == "docker_network_rx":
            return stats.get("network_rx")
        elif self._sensor_type == "docker_network_tx":
            return stats.get("network_tx")

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        container_data = self.coordinator.get_docker_data(self._container_id)
        if not container_data:
            return {}

        container_info = container_data.get("system_info", {})
        stats = container_data.get("stats", {})

        attributes = {
            "container_id": self._container_id,
            "container_name": container_info.get("name"),
            "image": container_info.get("image"),
            "status": container_info.get("status"),
            "created": container_info.get("created"),
            "updated": container_info.get("updated"),
        }

        # Add additional stats as attributes
        if stats:
            attributes.update(
                {
                    "cpu_percent": stats.get("cpu_percent"),
                    "memory_percent": stats.get("memory_percent"),
                    "memory_usage": stats.get("memory_usage"),
                    "memory_limit": stats.get("memory_limit"),
                    "network_rx": stats.get("network_rx"),
                    "network_tx": stats.get("network_tx"),
                    "block_io_read": stats.get("block_io_read"),
                    "block_io_write": stats.get("block_io_write"),
                }
            )

        return attributes

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        container_data = self.coordinator.get_docker_data(self._container_id)
        if not container_data:
            return False

        container_info = container_data.get("system_info", {})
        status = container_info.get("status", "").lower()

        # Container is available if it's running
        return status in ["running", "up"]
