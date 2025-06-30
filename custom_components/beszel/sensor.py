"""Support for Beszel sensors."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_TYPES
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
            system_info = system_data["system_info"]
            system_id = system_info.get("id")
            system_name = system_info.get("name", f"System {system_id}")
            
            # Create sensors for each metric type
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
        if not system_data or "stats" not in system_data:
            return None
            
        stats = system_data["stats"]
        if not stats:
            return None
        
        # Extract the appropriate value based on sensor type
        if self._sensor_type == "cpu":
            return stats.get("cpu", {}).get("usage")
        elif self._sensor_type == "ram":
            ram_data = stats.get("memory", {})
            used = ram_data.get("used", 0)
            total = ram_data.get("total", 1)
            return round((used / total) * 100, 1) if total > 0 else None
        elif self._sensor_type == "disk":
            disk_data = stats.get("disk", {})
            used = disk_data.get("used", 0)
            total = disk_data.get("total", 1)
            return round((used / total) * 100, 1) if total > 0 else None
        elif self._sensor_type == "network_up":
            return stats.get("network", {}).get("upload", 0) / (1024 * 1024)  # Convert to MB/s
        elif self._sensor_type == "network_down":
            return stats.get("network", {}).get("download", 0) / (1024 * 1024)  # Convert to MB/s
        elif self._sensor_type == "temperature":
            return stats.get("temperature", {}).get("main")
        elif self._sensor_type == "uptime":
            return stats.get("uptime")
        
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
        
        # Add detailed stats for specific sensor types
        if "stats" in system_data and system_data["stats"]:
            stats = system_data["stats"]
            
            if self._sensor_type == "ram":
                ram_data = stats.get("memory", {})
                attributes["used_gb"] = round(ram_data.get("used", 0) / (1024**3), 2)
                attributes["total_gb"] = round(ram_data.get("total", 0) / (1024**3), 2)
                attributes["free_gb"] = round(ram_data.get("free", 0) / (1024**3), 2)
            elif self._sensor_type == "disk":
                disk_data = stats.get("disk", {})
                attributes["used_gb"] = round(disk_data.get("used", 0) / (1024**3), 2)
                attributes["total_gb"] = round(disk_data.get("total", 0) / (1024**3), 2)
                attributes["free_gb"] = round(disk_data.get("free", 0) / (1024**3), 2)
        
        return attributes if attributes else None
