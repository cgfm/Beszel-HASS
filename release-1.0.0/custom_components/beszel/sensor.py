"""Support for Beszel sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
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
