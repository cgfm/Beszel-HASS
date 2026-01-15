"""Support for Beszel sensors."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_TYPES, SMART_SENSOR_TYPES
from .coordinator import BeszelDataUpdateCoordinator
from .device import async_remove_stale_entities, build_unique_id_prefixes

_LOGGER = logging.getLogger(__name__)


# System sensor types - uses SENSOR_TYPES from const.py
# Additional IP sensor not in const.py
SYSTEM_SENSOR_TYPES_EXTRA = {
    "ip": {
        "name": "IP Address",
        "icon": "mdi:ip-network",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "info_key": "host",
        "data_source": "system_info",  # Special case - from system record itself
    },
}

# Define sensor types for Docker containers
DOCKER_SENSOR_TYPES = {
    "cpu": {
        "name": "CPU Usage",
        "icon": "mdi:cpu-64-bit",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": PERCENTAGE,
        "key": "cpu",
    },
    "memory": {
        "name": "Memory Usage",
        "icon": "mdi:memory",
        "device_class": SensorDeviceClass.DATA_SIZE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfInformation.MEGABYTES,
        "key": "memory",
    },
    "network_sent": {
        "name": "Network Sent",
        "icon": "mdi:upload",
        "device_class": SensorDeviceClass.DATA_RATE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfDataRate.KILOBYTES_PER_SECOND,
        "key": "network_sent",
    },
    "network_received": {
        "name": "Network Received",
        "icon": "mdi:download",
        "device_class": SensorDeviceClass.DATA_RATE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfDataRate.KILOBYTES_PER_SECOND,
        "key": "network_received",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Beszel sensors based on a config entry."""
    coordinator: BeszelDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Create sensors for each system
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

                    for sensor_type, sensor_config in DOCKER_SENSOR_TYPES.items():
                        entities.append(
                            BeszelDockerSensor(
                                coordinator=coordinator,
                                container_id=system_id,
                                container_name=display_name,
                                sensor_type=sensor_type,
                                sensor_config=sensor_config,
                            )
                        )
            elif data_type == "smart":
                # Skip SMART devices in main loop - they are handled separately below
                # using coordinator.smart_devices which has the correct parent system ID
                continue
            else:
                # Handle regular systems
                system_name = system_info.get("name", f"System {system_id}")

                # Create sensors from const.py SENSOR_TYPES
                for sensor_type, sensor_config in SENSOR_TYPES.items():
                    entities.append(
                        BeszelSystemSensor(
                            coordinator=coordinator,
                            system_id=system_id,
                            system_name=system_name,
                            sensor_type=sensor_type,
                            sensor_config=sensor_config,
                        )
                    )

                # Create additional sensors (IP address)
                for sensor_type, sensor_config in SYSTEM_SENSOR_TYPES_EXTRA.items():
                    entities.append(
                        BeszelSystemSensor(
                            coordinator=coordinator,
                            system_id=system_id,
                            system_name=system_name,
                            sensor_type=sensor_type,
                            sensor_config=sensor_config,
                        )
                    )

    # Create sensors for SMART devices
    for smart_data in coordinator.smart_devices:
        smart_info = smart_data.get("system_info", {})
        disk_id = smart_info.get("disk_id")
        disk_model = smart_info.get("model", "Unknown Disk")
        device_path = smart_info.get("device", "")  # e.g., "/dev/sda"
        system_id = smart_info.get("system")
        system_name = smart_info.get("system_name", "Unknown System")
        smart_key = smart_data.get("system_id")  # e.g., "smart_abc123_sda"

        # Skip SMART devices whose parent system doesn't exist
        # This prevents creating orphan devices for removed systems
        if system_id and not coordinator.get_system_data(system_id):
            _LOGGER.debug(
                "Skipping SMART device %s - parent system %s not found",
                smart_key, system_id
            )
            continue

        if disk_id and smart_key and system_id:
            for sensor_type, sensor_config in SMART_SENSOR_TYPES.items():
                entities.append(
                    BeszelSmartSensor(
                        coordinator=coordinator,
                        smart_key=smart_key,
                        system_id=system_id,
                        system_name=system_name,
                        disk_id=disk_id,
                        disk_model=disk_model,
                        device_path=device_path,
                        sensor_type=sensor_type,
                        sensor_config=sensor_config,
                    )
                )

    async_add_entities(entities)

    @callback
    def _async_update_listener() -> None:
        """Handle coordinator updates and remove stale entities."""
        if coordinator.data:
            unique_id_prefixes = build_unique_id_prefixes(coordinator.data)
            async_remove_stale_entities(hass, entry, unique_id_prefixes)

    # Register listener to remove stale entities when coordinator updates
    entry.async_on_unload(coordinator.async_add_listener(_async_update_listener))


class BeszelSystemSensor(CoordinatorEntity[BeszelDataUpdateCoordinator], SensorEntity):
    """Representation of a Beszel system sensor."""

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
        self._attr_icon = sensor_config["icon"]
        self._attr_device_class = sensor_config.get("device_class")
        self._attr_state_class = sensor_config.get("state_class")
        self._attr_native_unit_of_measurement = sensor_config.get("unit")

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, system_id)},
            "name": system_name,
            "manufacturer": "Beszel",
            "model": "Server Monitor",
        }

    @property
    def native_value(self) -> str | float | int | None:
        """Return the state of the sensor."""
        system_data = self.coordinator.get_system_data(self._system_id)
        if not system_data:
            return None

        # Determine data source and get the value
        data_source = self._sensor_config.get("data_source", "stats")
        info_key = self._sensor_config.get("info_key", self._sensor_config.get("key"))

        value = None

        if data_source == "system_info":
            # Special case: directly from system_info (e.g., host/IP)
            system_info = system_data.get("system_info", {})
            value = system_info.get(info_key)
        elif data_source == "info":
            # From system_info.info object (cpu, memory %, disk %, etc.)
            system_info = system_data.get("system_info", {})
            info_obj = system_info.get("info", {})
            value = info_obj.get(info_key)
            # Debug: Log if info object is missing or key not found
            if not info_obj:
                _LOGGER.debug(
                    "Sensor %s: 'info' object is empty for system %s. system_info keys: %s",
                    self._sensor_type, self._system_id, list(system_info.keys())
                )
            elif value is None:
                _LOGGER.debug(
                    "Sensor %s: key '%s' not found in info object. Available keys: %s",
                    self._sensor_type, info_key, list(info_obj.keys())
                )
        elif data_source == "stats":
            # From stats object (network, disk io, load, etc.)
            stats = system_data.get("stats", {})
            value = stats.get(info_key)

            # Fallback: If stats is empty or key not found, try info object
            # The info object often contains the same metrics (cpu, la, b, etc.)
            if value is None:
                system_info = system_data.get("system_info", {})
                info_obj = system_info.get("info", {})
                value = info_obj.get(info_key)
                if value is not None:
                    _LOGGER.debug(
                        "Sensor %s: using fallback from info object for system %s",
                        self._sensor_type, self._system_id
                    )

            # Debug: Log if both stats and info object are missing the key
            if value is None:
                if not stats:
                    _LOGGER.debug(
                        "Sensor %s: 'stats' object is empty for system %s",
                        self._sensor_type, self._system_id
                    )
                else:
                    _LOGGER.debug(
                        "Sensor %s: key '%s' not found in stats object. Available keys: %s",
                        self._sensor_type, info_key, list(stats.keys())
                    )

        # Handle array values (e.g., load average [1m, 5m, 15m])
        array_index = self._sensor_config.get("array_index")
        if array_index is not None and isinstance(value, list):
            if len(value) > array_index:
                value = value[array_index]
            else:
                value = None

        # Convert value if necessary
        if value is not None:
            try:
                # Percentages
                if self._sensor_type in ["cpu", "memory", "disk", "gpu", "battery", "load_1", "load_5", "load_15"]:
                    return round(float(value), 1)
                # Temperature
                elif self._sensor_type in ["disk_temp"]:
                    return round(float(value), 1)
                # Duration (uptime)
                elif self._sensor_type == "uptime":
                    return int(value)
                # Data rates (network, disk io)
                elif self._sensor_type in ["network_sent", "network_recv", "disk_read", "disk_write"]:
                    return round(float(value), 2)
                # Data sizes (memory, swap in GB)
                elif self._sensor_type in ["memory_used", "memory_total", "swap_used", "swap_total", "bandwidth"]:
                    return round(float(value), 2)
                else:
                    return value
            except (ValueError, TypeError):
                _LOGGER.debug(
                    "Could not convert value %s for sensor %s", value, self._sensor_type
                )
                return None

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

        system_info = system_data.get("system_info", {})
        info_obj = system_info.get("info", {})
        stats = system_data.get("stats", {})

        attributes = {
            "system_id": self._system_id,
            "system_name": system_info.get("name"),
            "last_updated": system_info.get("updated"),
        }

        # Add additional stats for context based on sensor type
        if self._sensor_type == "cpu":
            # CPU cores from info object
            attributes["cpu_cores"] = info_obj.get("c")
        elif self._sensor_type == "memory":
            # Memory totals from stats
            attributes["memory_total_gb"] = stats.get("m")
            attributes["memory_used_gb"] = stats.get("mu")
        elif self._sensor_type == "disk":
            # Disk totals from stats
            attributes["disk_total_gb"] = stats.get("d")
            attributes["disk_used_gb"] = stats.get("du")

        return attributes


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

        # Create unique ID (v4 to force recreation and match binary sensor format)
        self._attr_unique_id = f"docker_{container_id}_{sensor_type}_v4"

        # Set entity name
        self._attr_name = f"Docker {container_name} {sensor_config['name']}"

        # Set sensor properties
        self._attr_icon = sensor_config["icon"]
        self._attr_device_class = sensor_config.get("device_class")
        self._attr_state_class = sensor_config.get("state_class")
        self._attr_native_unit_of_measurement = sensor_config.get("unit")

        # Set device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"docker_{container_id}")},
            "name": f"Docker: {container_name}",
            "manufacturer": "Docker",
            "model": "Container",
            "configuration_url": None,
        }

    @property
    def native_value(self) -> str | float | int | None:
        """Return the state of the sensor."""
        container_data = self.coordinator.get_docker_data(self._container_id)
        if not container_data:
            return None

        stats = container_data.get("stats", {})
        value = stats.get(self._sensor_config["key"])

        # Convert value if necessary
        if value is not None:
            try:
                if self._sensor_type == "cpu":
                    return round(float(value), 1)
                elif self._sensor_type == "memory":
                    # Memory is in bytes, convert to MB
                    return round(int(value) / (1024 * 1024), 1)
                elif self._sensor_type in ["network_sent", "network_received"]:
                    # Network is in bytes/s, convert to KB/s
                    return round(int(value) / 1024, 1)
                else:
                    return value
            except (ValueError, TypeError):
                _LOGGER.debug(
                    "Could not convert value %s for sensor %s", value, self._sensor_type
                )
                return None

        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.get_docker_data(self._container_id) is not None

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
            "system": container_info.get("system"),
            "system_name": container_info.get("system_name"),
            "updated": container_info.get("updated"),
        }


class BeszelSmartSensor(CoordinatorEntity[BeszelDataUpdateCoordinator], SensorEntity):
    """Representation of a Beszel SMART disk sensor."""

    def __init__(
        self,
        coordinator: BeszelDataUpdateCoordinator,
        smart_key: str,
        system_id: str,
        system_name: str,
        disk_id: str,
        disk_model: str,
        device_path: str,
        sensor_type: str,
        sensor_config: dict[str, Any],
    ) -> None:
        """Initialize the SMART sensor."""
        super().__init__(coordinator)

        # Set enabled default from config (defaults to True if not specified)
        self._attr_entity_registry_enabled_default = sensor_config.get("enabled_default", True)

        self._smart_key = smart_key
        self._system_id = system_id
        self._system_name = system_name
        self._disk_id = disk_id
        self._disk_model = disk_model
        self._device_path = device_path
        self._sensor_type = sensor_type
        self._sensor_config = sensor_config

        # Create a clean disk display name from device path (e.g., "/dev/sda" -> "sda")
        # Prefer device_path, fall back to disk_id if device_path is empty
        if device_path:
            # Extract device name from path (e.g., "/dev/sda" -> "sda", "/dev/nvme0n1" -> "nvme0n1")
            disk_display = device_path.replace("/dev/", "")
        elif disk_id and not (len(disk_id) == 8 and all(c in "0123456789abcdef" for c in disk_id.lower())):
            # disk_id is a device name like "sda" or "nvme0n1" (not a hex ID)
            disk_display = disk_id
        else:
            # Fall back to model or disk_id
            disk_display = disk_model if disk_model and disk_model != "Unknown Disk" else disk_id

        self._attr_name = f"{system_name} {disk_display} {sensor_config['name']}"
        self._attr_unique_id = f"smart_{system_id}_{disk_id}_{sensor_type}_v1"
        self._attr_icon = sensor_config["icon"]
        self._attr_device_class = sensor_config.get("device_class")
        self._attr_state_class = sensor_config.get("state_class")
        self._attr_native_unit_of_measurement = sensor_config.get("unit")

        # Group SMART sensors under the parent system device
        # Only specify identifiers to link to the existing system device
        # Do NOT specify name/manufacturer/model - that would create a new device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, system_id)},
        }

    @property
    def native_value(self) -> str | float | int | None:
        """Return the state of the sensor."""
        smart_data = self.coordinator.get_smart_data(self._smart_key)
        if not smart_data:
            return None

        stats = smart_data.get("stats", {})

        # Handle different sensor types
        if self._sensor_type == "health":
            return stats.get("state")

        elif self._sensor_type == "temperature":
            temp = stats.get("temp")
            if temp is not None:
                try:
                    return round(float(temp), 1)
                except (ValueError, TypeError):
                    return None
            return None

        else:
            # Handle SMART attributes (reallocated_sectors, pending_sectors, etc.)
            attr_id = self._sensor_config.get("attr_id")
            if attr_id is not None:
                attributes = stats.get("attributes", {})
                value = attributes.get(attr_id)
                if value is not None:
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return None
            return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.get_smart_data(self._smart_key) is not None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        smart_data = self.coordinator.get_smart_data(self._smart_key)
        if not smart_data:
            return {}

        smart_info = smart_data.get("system_info", {})
        stats = smart_data.get("stats", {})

        attributes = {
            "system_id": self._system_id,
            "system_name": self._system_name,
            "disk_id": self._disk_id,
            "disk_model": self._disk_model,
            "device_path": self._device_path,
            "last_updated": smart_info.get("updated"),
        }

        # Add all SMART attributes for debugging/advanced users
        if self._sensor_type == "health":
            smart_attrs = stats.get("attributes", {})
            if smart_attrs:
                attributes["smart_attributes"] = smart_attrs

        return attributes
