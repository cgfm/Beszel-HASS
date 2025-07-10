"""Support for Beszel sensors."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOCKER_SENSOR_TYPES, DOMAIN, SENSOR_TYPES
from .coordinator import BeszelDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


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
                    system_name = system_info.get("system_name", "Unknown System")

                    # Create display name with system context
                    display_name = f"{container_name} ({system_name})"

                    for sensor_type, sensor_config in DOCKER_SENSOR_TYPES.items():
                        entities.append(
                            BeszelDockerSensor(
                                coordinator=coordinator,
                                container_id=system_id,
                                container_name=display_name,
                                system_name=system_name,
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
        self._attr_unique_id = f"{system_id}_{sensor_type}_v4"
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
        system_name: str,
        sensor_type: str,
        sensor_config: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._container_id = container_id
        self._container_name = container_name
        self._system_name = system_name
        self._sensor_type = sensor_type
        self._sensor_config = sensor_config

        # Create unique ID with system name prefix (v5 to force recreation)
        # Sanitize system name for use in unique_id (remove spaces and special chars)
        system_prefix = (
            system_name.lower()
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("-", "_")
        )
        self._attr_unique_id = f"{system_prefix}_docker_{container_id}_{sensor_type}_v5"

        # Set entity name
        self._attr_name = f"Docker {container_name} {sensor_config['name']}"

        # Set device info with system context
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{system_prefix}_docker_{container_id}")},
            "name": f"Docker: {container_name}",
            "manufacturer": "Docker",
            "model": "Container",
            "configuration_url": None,
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
        _LOGGER.debug(
            "DEBUG: Getting native_value for container_id=%s, sensor_type=%s",
            self._container_id,
            self._sensor_type,
        )

        container_data = self.coordinator.get_docker_data(self._container_id)

        _LOGGER.debug(
            "DEBUG: Container data for %s: %s",
            self._container_id,
            "Found" if container_data else "NOT FOUND",
        )

        if not container_data:
            _LOGGER.warning(
                "No container data found for container_id: %s", self._container_id
            )
            return None

        stats = container_data.get("stats", {})

        _LOGGER.debug(
            "DEBUG: Stats for %s: type=%s, keys=%s",
            self._container_id,
            type(stats).__name__,
            list(stats.keys()) if isinstance(stats, dict) else "N/A",
        )

        if not stats:
            _LOGGER.warning("No stats found for container %s", self._container_id)
            return None

        # Extract values based on sensor type using the correct Beszel field mapping
        sensor_mappings = {
            "docker_cpu": "cpu",  # from 'c' field (percentage)
            "docker_memory_bytes": "memory",  # from 'm' field (MB from API - convert to bytes)
            "docker_network_rx": "network_received",  # from 'nr' field (MB/s from API - convert to bytes/s)
            "docker_network_tx": "network_sent",  # from 'ns' field (MB/s from API - convert to bytes/s)
        }

        field_name = sensor_mappings.get(self._sensor_type)
        _LOGGER.debug(
            "DEBUG: sensor_type=%s, field_name=%s, available_stats_keys=%s",
            self._sensor_type,
            field_name,
            list(stats.keys()) if stats else "None",
        )

        if field_name and field_name in stats:
            value = stats[field_name]

            _LOGGER.debug(
                "DEBUG: Found value for %s.%s = %s (field: %s)",
                self._container_id,
                self._sensor_type,
                value,
                field_name,
            )

            # Convert to appropriate type and unit
            if isinstance(value, (int, float)):
                # Convert MB values from API to bytes for Home Assistant
                if self._sensor_type in [
                    "docker_memory_bytes",
                    "docker_network_rx",
                    "docker_network_tx",
                ]:
                    # API sends MB, convert to bytes for Home Assistant auto-formatting
                    converted_value = float(value) * 1024 * 1024  # MB to bytes
                    _LOGGER.debug(
                        "DEBUG: Converted %s MB to %s bytes", value, converted_value
                    )
                    return round(converted_value, 0)  # No decimals for bytes
                else:
                    return round(float(value), 2)
            return value

        # Fallback: try raw field access for debugging
        if "raw" in stats:
            raw_data = stats["raw"]
            _LOGGER.debug(
                "DEBUG: Using raw fallback for %s, raw_data keys: %s",
                self._container_id,
                list(raw_data.keys()) if isinstance(raw_data, dict) else "N/A",
            )

            fallback_mappings = {
                "docker_cpu": "c",
                "docker_memory_bytes": "m",  # MB value from API (convert to bytes)
                "docker_network_rx": "nr",  # MB/s value from API (convert to bytes/s)
                "docker_network_tx": "ns",  # MB/s value from API (convert to bytes/s)
            }

            fallback_key = fallback_mappings.get(self._sensor_type)
            if fallback_key and fallback_key in raw_data:
                value = raw_data[fallback_key]
                _LOGGER.debug(
                    "DEBUG: Found fallback value for %s.%s = %s",
                    self._container_id,
                    fallback_key,
                    value,
                )

                if isinstance(value, (int, float)):
                    # Convert MB values from API to bytes for Home Assistant
                    if self._sensor_type in [
                        "docker_memory_bytes",
                        "docker_network_rx",
                        "docker_network_tx",
                    ]:
                        # API sends MB, convert to bytes for Home Assistant auto-formatting
                        converted_value = float(value) * 1024 * 1024  # MB to bytes
                        _LOGGER.debug(
                            "DEBUG: Fallback converted %s MB to %s bytes",
                            value,
                            converted_value,
                        )
                        return round(converted_value, 0)  # No decimals for bytes
                    else:
                        return round(float(value), 2)
                return value

        _LOGGER.warning(
            "No value found for sensor %s.%s (checked: %s, fallback: %s)",
            self._container_id,
            self._sensor_type,
            field_name,
            (
                fallback_mappings.get(self._sensor_type)
                if "fallback_mappings" in locals()
                else "N/A"
            ),
        )
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
            "system_id": container_info.get("system"),
            "system_name": container_info.get("system_name"),
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
        # If the container is returned by the API, it's available
        # The API only returns containers that exist
        container_data = self.coordinator.get_docker_data(self._container_id)
        is_available = container_data is not None

        _LOGGER.debug(
            "DEBUG: Container %s available check: %s", self._container_id, is_available
        )

        return is_available
