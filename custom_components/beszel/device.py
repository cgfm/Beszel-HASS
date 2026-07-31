"""Device and registry helpers for Beszel."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import (
    DOCKER_SENSOR_DESCRIPTIONS,
    DOMAIN,
    EXTRA_DISK_SENSOR_DESCRIPTIONS,
    SMART_SENSOR_DESCRIPTIONS,
    SYSTEM_SENSOR_DESCRIPTIONS,
)
from .coordinator import BeszelDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def entity_unique_id(
    coordinator: BeszelDataUpdateCoordinator,
    kind: str,
    record_id: str,
    metric: str,
) -> str:
    """Return a stable, hub-scoped entity unique ID."""
    return f"{coordinator.namespace}:{kind}:{record_id}:{metric}"


def device_identifier(
    coordinator: BeszelDataUpdateCoordinator, kind: str, record_id: str
) -> tuple[str, str]:
    """Return a stable, hub-scoped device identifier."""
    return (DOMAIN, f"{coordinator.namespace}:{kind}:{record_id}")


@callback
def async_remove_entity(
    hass: HomeAssistant,
    platform: str,
    entity: Entity,
) -> None:
    """Remove an exact entity from both the registry and the running platform."""
    registry = er.async_get(hass)
    if entity.unique_id:
        entity_id = registry.async_get_entity_id(platform, DOMAIN, entity.unique_id)
        if entity_id:
            registry.async_remove(entity_id)
    if entity.hass is not None:
        hass.async_create_task(entity.async_remove(force_remove=True))


@callback
def async_remove_device_if_empty(
    hass: HomeAssistant,
    coordinator: BeszelDataUpdateCoordinator,
    kind: str,
    record_id: str,
) -> None:
    """Remove an exact Beszel device after its final entity is gone."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(
        identifiers={device_identifier(coordinator, kind, record_id)}
    )
    if device is None or er.async_entries_for_device(
        entity_registry, device.id, include_disabled_entities=True
    ):
        return
    device_registry.async_remove_device(device.id)


@callback
def async_remove_empty_devices(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove empty Beszel devices left behind by migration or disabled features."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    for device in list(
        device_registry.devices.get_devices_for_config_entry_id(entry.entry_id)
    ):
        if not any(identifier[0] == DOMAIN for identifier in device.identifiers):
            continue
        if er.async_entries_for_device(
            entity_registry, device.id, include_disabled_entities=True
        ):
            continue
        device_registry.async_remove_device(device.id)


def system_device_info(
    coordinator: BeszelDataUpdateCoordinator, system: dict[str, Any]
) -> DeviceInfo:
    """Build device info for a monitored system."""
    return DeviceInfo(
        identifiers={device_identifier(coordinator, "system", system["id"])},
        name=system["name"],
        manufacturer="Beszel",
        model="Monitored system",
        sw_version=system.get("agent_version"),
        configuration_url=coordinator.api.base_url,
    )


def container_device_info(
    coordinator: BeszelDataUpdateCoordinator, container: dict[str, Any]
) -> DeviceInfo:
    """Build device info for a Docker or Podman container."""
    return DeviceInfo(
        identifiers={device_identifier(coordinator, "container", container["id"])},
        name=f"{container['name']} ({container['system_name']})",
        manufacturer="Beszel",
        model="Container",
        via_device=device_identifier(coordinator, "system", container["system_id"]),
        configuration_url=coordinator.api.base_url,
    )


def smart_device_info(
    coordinator: BeszelDataUpdateCoordinator, disk: dict[str, Any]
) -> DeviceInfo:
    """Build device info for one SMART disk."""
    return DeviceInfo(
        identifiers={device_identifier(coordinator, "smart", disk["id"])},
        name=f"{disk['model']} ({disk['disk_id']})",
        manufacturer="Beszel",
        model=disk["model"],
        via_device=device_identifier(coordinator, "system", disk["system_id"]),
        configuration_url=coordinator.api.base_url,
    )


@callback
def async_migrate_legacy_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: BeszelDataUpdateCoordinator,
) -> None:
    """Migrate v1.1 unique IDs and remove the invalid disk-temperature entity."""
    registry = er.async_get(hass)
    mappings: dict[str, str] = {}
    obsolete: set[str] = set()
    expected: set[str] = set()

    system_metric_map = {
        "cpu": "cpu",
        "cpu_cores": "cpu_cores",
        "cpu_temp": "temperature",
        "memory": "memory",
        "disk": "disk",
        "disk_total": "disk_total",
        "disk_used": "disk_used",
        "uptime": "uptime",
        "bandwidth": "bandwidth",
        "load_1": "load_1",
        "load_5": "load_5",
        "load_15": "load_15",
        "gpu": "gpu",
        "battery": "battery",
        "disk_read": "disk_read",
        "disk_write": "disk_write",
        "network_sent": "network_sent",
        "network_recv": "network_received",
        "memory_used": "memory_used",
        "memory_total": "memory_total",
        "memory_buffered": "memory_buffered",
        "swap_used": "swap_used",
        "swap_total": "swap_total",
        "ip": "ip",
    }
    for system_id, system in coordinator.systems.items():
        for old_metric, new_metric in system_metric_map.items():
            new_unique_id = entity_unique_id(
                coordinator, "system", system_id, new_metric
            )
            mappings[f"{system_id}_{old_metric}_v4"] = new_unique_id
            expected.add(new_unique_id)
        status_unique_id = entity_unique_id(coordinator, "system", system_id, "status")
        mappings[f"{system_id}_status_v4"] = status_unique_id
        expected.add(status_unique_id)
        obsolete.add(f"{system_id}_disk_temp_v4")
        for filesystem in system.get("filesystems", {}):
            for metric in ("usage", "total", "used", "read", "write"):
                new_unique_id = entity_unique_id(
                    coordinator,
                    "filesystem",
                    f"{system_id}:{filesystem}",
                    metric,
                )
                mappings[f"{system_id}_efs_{filesystem}_{metric}_v1"] = new_unique_id
                expected.add(new_unique_id)

    for container_id, container in coordinator.containers.items():
        legacy_ids = {
            container_id,
            f"{container['system_name']}_{container['name']}",
        }
        for legacy_id in legacy_ids:
            for metric in ("cpu", "memory", "network_sent", "network_received"):
                new_unique_id = entity_unique_id(
                    coordinator, "container", container_id, metric
                )
                mappings[f"docker_{legacy_id}_{metric}_v4"] = new_unique_id
                expected.add(new_unique_id)
            status_unique_id = entity_unique_id(
                coordinator, "container", container_id, "status"
            )
            mappings[f"docker_{legacy_id}_status_v4"] = status_unique_id
            expected.add(status_unique_id)

    for disk_id, disk in coordinator.smart_devices.items():
        for metric in (
            "health",
            "temperature",
            "reallocated_sectors",
            "pending_sectors",
            "uncorrectable_sectors",
            "power_on_hours",
        ):
            new_unique_id = entity_unique_id(coordinator, "smart", disk_id, metric)
            mappings[f"smart_{disk['system_id']}_{disk['disk_id']}_{metric}_v1"] = (
                new_unique_id
            )
            expected.add(new_unique_id)

    # Include all descriptions independently of the legacy mapping tables so a
    # changed endpoint can retain compatible v2 entities and discard the rest.
    for system_id, system in coordinator.systems.items():
        expected.update(
            entity_unique_id(coordinator, "system", system_id, description.key)
            for description in SYSTEM_SENSOR_DESCRIPTIONS
        )
        expected.update(
            entity_unique_id(
                coordinator,
                "filesystem",
                f"{system_id}:{filesystem}",
                description.key,
            )
            for filesystem in system.get("filesystems", {})
            for description in EXTRA_DISK_SENSOR_DESCRIPTIONS
        )
    for container_id in coordinator.containers:
        expected.update(
            entity_unique_id(coordinator, "container", container_id, description.key)
            for description in DOCKER_SENSOR_DESCRIPTIONS
        )
    for disk_id in coordinator.smart_devices:
        expected.update(
            entity_unique_id(coordinator, "smart", disk_id, description.key)
            for description in SMART_SENSOR_DESCRIPTIONS
        )

    for entity in list(registry.entities.values()):
        if entity.config_entry_id != entry.entry_id or not entity.unique_id:
            continue
        if entity.unique_id in obsolete:
            registry.async_remove(entity.entity_id)
            continue
        new_unique_id = mappings.get(entity.unique_id)
        namespace, separator, suffix = entity.unique_id.partition(":")
        if (
            new_unique_id is None
            and separator
            and namespace != coordinator.namespace
            and len(namespace) == 12
            and all(char in "0123456789abcdef" for char in namespace)
            and suffix.split(":", 1)[0]
            in {"system", "filesystem", "container", "smart"}
        ):
            candidate = f"{coordinator.namespace}:{suffix}"
            if candidate in expected:
                new_unique_id = candidate
            else:
                registry.async_remove(entity.entity_id)
                continue
        if new_unique_id is None or new_unique_id == entity.unique_id:
            continue
        platform = entity.entity_id.split(".", 1)[0]
        existing = registry.async_get_entity_id(platform, DOMAIN, new_unique_id)
        if existing and existing != entity.entity_id:
            existing_entry = registry.async_get(existing)
            if existing_entry and existing_entry.config_entry_id == entry.entry_id:
                registry.async_remove(entity.entity_id)
                continue
            _LOGGER.warning(
                "Cannot migrate %s because %s already owns the target unique ID",
                entity.entity_id,
                existing,
            )
            continue
        registry.async_update_entity(entity.entity_id, new_unique_id=new_unique_id)


@callback
def async_remove_docker_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: BeszelDataUpdateCoordinator,
) -> None:
    """Remove only entities known to belong to disabled Docker support."""
    registry = er.async_get(hass)
    prefix = f"{coordinator.namespace}:container:"
    for entity in list(registry.entities.values()):
        if entity.config_entry_id != entry.entry_id or not entity.unique_id:
            continue
        if entity.unique_id.startswith(prefix) or entity.unique_id.startswith(
            "docker_"
        ):
            registry.async_remove(entity.entity_id)
    async_remove_empty_devices(hass, entry)
