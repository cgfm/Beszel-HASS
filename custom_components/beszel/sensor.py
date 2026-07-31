"""Sensor platform for Beszel."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOCKER_SENSOR_DESCRIPTIONS,
    DOMAIN,
    EXTRA_DISK_SENSOR_DESCRIPTIONS,
    SMART_SENSOR_DESCRIPTIONS,
    STALE_UPDATE_LIMIT,
    SYSTEM_SENSOR_DESCRIPTIONS,
)
from .coordinator import BeszelDataUpdateCoordinator
from .device import (
    async_remove_device_if_empty,
    async_remove_entity,
    container_device_info,
    entity_unique_id,
    smart_device_info,
    system_device_info,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Beszel sensors and discover later inventory changes."""
    coordinator: BeszelDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    manager = BeszelSensorManager(hass, coordinator, async_add_entities)
    manager.async_update_entities()
    entry.async_on_unload(coordinator.async_add_listener(manager.async_update_entities))


class BeszelSensorManager:
    """Add and remove exact entity groups as Beszel inventory changes."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: BeszelDataUpdateCoordinator,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        self._hass = hass
        self._coordinator = coordinator
        self._async_add_entities = async_add_entities
        self._targets: dict[str, list[SensorEntity]] = {}
        self._filesystem_misses: dict[str, int] = {}

    @callback
    def async_update_entities(self) -> None:
        """Discover new records and retire confirmed-deleted records."""
        current: set[str] = set()
        new_entities: list[SensorEntity] = []

        for system_id, system in self._coordinator.systems.items():
            target = f"system:{system_id}"
            current.add(target)
            if target not in self._targets:
                entities = [
                    BeszelSystemSensor(self._coordinator, system_id, description)
                    for description in SYSTEM_SENSOR_DESCRIPTIONS
                ]
                self._targets[target] = entities
                new_entities.extend(entities)

            for filesystem in system.get("filesystems", {}):
                target = f"filesystem:{system_id}:{filesystem}"
                current.add(target)
                self._filesystem_misses.pop(target, None)
                if target in self._targets:
                    continue
                entities = [
                    BeszelFilesystemSensor(
                        self._coordinator,
                        system_id,
                        filesystem,
                        description,
                    )
                    for description in EXTRA_DISK_SENSOR_DESCRIPTIONS
                ]
                self._targets[target] = entities
                new_entities.extend(entities)

        for container_id in self._coordinator.containers:
            target = f"container:{container_id}"
            current.add(target)
            if target in self._targets:
                continue
            entities = [
                BeszelContainerSensor(self._coordinator, container_id, description)
                for description in DOCKER_SENSOR_DESCRIPTIONS
            ]
            self._targets[target] = entities
            new_entities.extend(entities)

        for disk_id in self._coordinator.smart_devices:
            target = f"smart:{disk_id}"
            current.add(target)
            if target in self._targets:
                continue
            entities = [
                BeszelSmartSensor(self._coordinator, disk_id, description)
                for description in SMART_SENSOR_DESCRIPTIONS
            ]
            self._targets[target] = entities
            new_entities.extend(entities)

        if new_entities:
            self._async_add_entities(new_entities)

        device_candidates: set[tuple[str, str]] = set()
        for target in set(self._targets) - current:
            if target.startswith("filesystem:"):
                parent_id = target.split(":", 2)[1]
                complete = self._coordinator.data.get("complete", {})
                if parent_id in self._coordinator.systems and not complete.get(
                    "system_stats", False
                ):
                    continue
                self._filesystem_misses[target] = (
                    self._filesystem_misses.get(target, 0) + 1
                )
                if (
                    parent_id in self._coordinator.systems
                    and self._filesystem_misses[target] < STALE_UPDATE_LIMIT
                ):
                    continue
                self._filesystem_misses.pop(target, None)
            for entity in self._targets.pop(target):
                async_remove_entity(self._hass, "sensor", entity)
            kind, record_id = target.split(":", 1)
            if kind == "filesystem":
                parent_id = record_id.split(":", 1)[0]
                if parent_id not in self._coordinator.systems:
                    device_candidates.add(("system", parent_id))
            else:
                device_candidates.add((kind, record_id))

        for kind, record_id in device_candidates:
            async_remove_device_if_empty(
                self._hass,
                self._coordinator,
                kind,
                record_id,
            )


class BeszelSystemSensor(CoordinatorEntity[BeszelDataUpdateCoordinator], SensorEntity):
    """One normalized system metric."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BeszelDataUpdateCoordinator,
        system_id: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._system_id = system_id
        self._attr_unique_id = entity_unique_id(
            coordinator, "system", system_id, description.key
        )
        self._attr_device_info = system_device_info(
            coordinator, coordinator.systems[system_id]
        )

    @property
    def native_value(self) -> Any:
        system = self.coordinator.get_system_data(self._system_id)
        return (
            system.get("metrics", {}).get(self.entity_description.key)
            if system
            else None
        )

    @property
    def available(self) -> bool:
        system = self.coordinator.get_system_data(self._system_id)
        return bool(
            self.coordinator.last_update_success
            and system
            and not system.get("stale")
            and system.get("status") == "up"
            and self.native_value is not None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        system = self.coordinator.get_system_data(self._system_id)
        if not system:
            return None
        return {
            "system_id": self._system_id,
            "host": system.get("host"),
            "status": system.get("status"),
            "last_updated": system.get("updated"),
        }


class BeszelFilesystemSensor(
    CoordinatorEntity[BeszelDataUpdateCoordinator], SensorEntity
):
    """One extra filesystem metric."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BeszelDataUpdateCoordinator,
        system_id: str,
        filesystem: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._system_id = system_id
        self._filesystem = filesystem
        display_name = filesystem.split("__", 1)[-1]
        self._attr_translation_placeholders = {"disk": display_name}
        self._attr_unique_id = entity_unique_id(
            coordinator,
            "filesystem",
            f"{system_id}:{filesystem}",
            description.key,
        )
        self._attr_device_info = system_device_info(
            coordinator, coordinator.systems[system_id]
        )

    @property
    def native_value(self) -> Any:
        system = self.coordinator.get_system_data(self._system_id)
        if not system:
            return None
        filesystem = system.get("filesystems", {}).get(self._filesystem)
        return filesystem.get(self.entity_description.key) if filesystem else None

    @property
    def available(self) -> bool:
        system = self.coordinator.get_system_data(self._system_id)
        return bool(
            self.coordinator.last_update_success
            and system
            and not system.get("stale")
            and system.get("status") == "up"
            and self.native_value is not None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"system_id": self._system_id, "filesystem": self._filesystem}


class BeszelContainerSensor(
    CoordinatorEntity[BeszelDataUpdateCoordinator], SensorEntity
):
    """One normalized container metric."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BeszelDataUpdateCoordinator,
        container_id: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._container_id = container_id
        self._attr_unique_id = entity_unique_id(
            coordinator, "container", container_id, description.key
        )
        self._attr_device_info = container_device_info(
            coordinator, coordinator.containers[container_id]
        )

    @property
    def native_value(self) -> Any:
        container = self.coordinator.get_docker_data(self._container_id)
        return (
            container.get("metrics", {}).get(self.entity_description.key)
            if container
            else None
        )

    @property
    def available(self) -> bool:
        container = self.coordinator.get_docker_data(self._container_id)
        parent = (
            self.coordinator.get_system_data(container["system_id"])
            if container
            else None
        )
        return bool(
            self.coordinator.last_update_success
            and container
            and not container.get("stale")
            and parent
            and not parent.get("stale")
            and parent.get("status") == "up"
            and self.native_value is not None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        container = self.coordinator.get_docker_data(self._container_id)
        if not container:
            return None
        return {
            "container_id": self._container_id,
            "system_id": container.get("system_id"),
            "status": container.get("status"),
            "health": container.get("health"),
            "image": container.get("image"),
            "last_updated": container.get("updated"),
        }


class BeszelSmartSensor(CoordinatorEntity[BeszelDataUpdateCoordinator], SensorEntity):
    """One normalized SMART disk metric."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BeszelDataUpdateCoordinator,
        disk_id: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._disk_id = disk_id
        self._attr_unique_id = entity_unique_id(
            coordinator, "smart", disk_id, description.key
        )
        self._attr_device_info = smart_device_info(
            coordinator, coordinator.smart_devices[disk_id]
        )

    @property
    def native_value(self) -> Any:
        disk = self.coordinator.get_smart_data(self._disk_id)
        return (
            disk.get("metrics", {}).get(self.entity_description.key) if disk else None
        )

    @property
    def available(self) -> bool:
        disk = self.coordinator.get_smart_data(self._disk_id)
        return bool(
            self.coordinator.last_update_success
            and disk
            and not disk.get("stale")
            and self.native_value is not None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        disk = self.coordinator.get_smart_data(self._disk_id)
        if not disk:
            return None
        attributes: dict[str, Any] = {
            "system_id": disk.get("system_id"),
            "device": disk.get("device"),
            "model": disk.get("model"),
            "serial": disk.get("serial"),
            "firmware": disk.get("firmware"),
            "disk_type": disk.get("disk_type"),
            "capacity_bytes": disk.get("capacity"),
            "power_cycles": disk.get("power_cycles"),
            "last_updated": disk.get("updated"),
        }
        if self.entity_description.key == "health":
            attributes["smart_attributes"] = {
                str(key): value for key, value in disk.get("attributes", {}).items()
            }
        return attributes
