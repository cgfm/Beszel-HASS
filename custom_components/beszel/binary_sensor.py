"""Binary sensor platform for Beszel."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BeszelDataUpdateCoordinator
from .device import (
    async_remove_device_if_empty,
    async_remove_entity,
    container_device_info,
    entity_unique_id,
    system_device_info,
)

SYSTEM_STATUS_DESCRIPTION = BinarySensorEntityDescription(
    key="status",
    translation_key="status",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
)
CONTAINER_STATUS_DESCRIPTION = BinarySensorEntityDescription(
    key="status",
    translation_key="status",
    device_class=BinarySensorDeviceClass.RUNNING,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Beszel binary sensors and later inventory changes."""
    coordinator: BeszelDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    manager = BeszelBinarySensorManager(hass, coordinator, async_add_entities)
    manager.async_update_entities()
    entry.async_on_unload(coordinator.async_add_listener(manager.async_update_entities))


class BeszelBinarySensorManager:
    """Manage dynamic system and container status entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: BeszelDataUpdateCoordinator,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        self._hass = hass
        self._coordinator = coordinator
        self._async_add_entities = async_add_entities
        self._targets: dict[str, BinarySensorEntity] = {}

    @callback
    def async_update_entities(self) -> None:
        current: set[str] = set()
        new_entities: list[BinarySensorEntity] = []
        for system_id in self._coordinator.systems:
            target = f"system:{system_id}"
            current.add(target)
            if target not in self._targets:
                entity = BeszelSystemBinarySensor(self._coordinator, system_id)
                self._targets[target] = entity
                new_entities.append(entity)
        for container_id in self._coordinator.containers:
            target = f"container:{container_id}"
            current.add(target)
            if target not in self._targets:
                entity = BeszelContainerBinarySensor(self._coordinator, container_id)
                self._targets[target] = entity
                new_entities.append(entity)
        if new_entities:
            self._async_add_entities(new_entities)
        for target in set(self._targets) - current:
            entity = self._targets.pop(target)
            async_remove_entity(self._hass, "binary_sensor", entity)
            kind, record_id = target.split(":", 1)
            async_remove_device_if_empty(
                self._hass,
                self._coordinator,
                kind,
                record_id,
            )


class BeszelSystemBinarySensor(
    CoordinatorEntity[BeszelDataUpdateCoordinator], BinarySensorEntity
):
    """System connectivity reported by Beszel."""

    _attr_has_entity_name = True
    entity_description = SYSTEM_STATUS_DESCRIPTION

    def __init__(
        self, coordinator: BeszelDataUpdateCoordinator, system_id: str
    ) -> None:
        super().__init__(coordinator)
        self._system_id = system_id
        self._attr_unique_id = entity_unique_id(
            coordinator, "system", system_id, "status"
        )
        self._attr_device_info = system_device_info(
            coordinator, coordinator.systems[system_id]
        )

    @property
    def is_on(self) -> bool:
        system = self.coordinator.get_system_data(self._system_id)
        return bool(system and system.get("status") == "up")

    @property
    def available(self) -> bool:
        system = self.coordinator.get_system_data(self._system_id)
        return bool(
            self.coordinator.last_update_success and system and not system.get("stale")
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        system = self.coordinator.get_system_data(self._system_id)
        if not system:
            return None
        return {
            "system_id": self._system_id,
            "host": system.get("host"),
            "port": system.get("port"),
            "status": system.get("status"),
            "last_updated": system.get("updated"),
        }


class BeszelContainerBinarySensor(
    CoordinatorEntity[BeszelDataUpdateCoordinator], BinarySensorEntity
):
    """Actual container running state reported by Beszel."""

    _attr_has_entity_name = True
    entity_description = CONTAINER_STATUS_DESCRIPTION

    def __init__(
        self, coordinator: BeszelDataUpdateCoordinator, container_id: str
    ) -> None:
        super().__init__(coordinator)
        self._container_id = container_id
        self._attr_unique_id = entity_unique_id(
            coordinator, "container", container_id, "status"
        )
        self._attr_device_info = container_device_info(
            coordinator, coordinator.containers[container_id]
        )

    @property
    def is_on(self) -> bool:
        container = self.coordinator.get_docker_data(self._container_id)
        return bool(container and container.get("running"))

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
            and parent
            and not parent.get("stale")
            and parent.get("status") == "up"
            and (not container.get("stale") or container.get("status") == "missing")
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
            "ports": container.get("ports"),
            "last_updated": container.get("updated"),
        }
