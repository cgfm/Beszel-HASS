"""The Beszel integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_INCLUDE_DOCKER, DOMAIN
from .coordinator import BeszelDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Beszel from a config entry."""
    coordinator = BeszelDataUpdateCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Get valid system IDs before setting up platforms
    valid_system_ids: set[str] = set()
    if coordinator.data:
        for key, system_data in coordinator.data.items():
            # Only add regular system IDs (not docker_ or smart_ prefixed)
            if not key.startswith("docker_") and not key.startswith("smart_"):
                valid_system_ids.add(key)
        _LOGGER.debug("Valid system IDs during setup: %s", valid_system_ids)

    # Clean up orphan devices BEFORE setting up platforms
    await async_remove_orphan_devices(hass, entry, valid_system_ids)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for config entry updates
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    # Check if Docker was disabled - if so, remove Docker entities before reload
    include_docker = entry.data.get(CONF_INCLUDE_DOCKER, True)
    if not include_docker:
        _LOGGER.info("Docker support disabled, removing Docker entities")
        await async_remove_docker_entities(hass, entry)

    # Get valid system IDs from the coordinator before cleanup
    valid_system_ids: set[str] = set()
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator and coordinator.data:
        for key, system_data in coordinator.data.items():
            # Only add regular system IDs (not docker_ or smart_ prefixed)
            if not key.startswith("docker_") and not key.startswith("smart_"):
                valid_system_ids.add(key)
        _LOGGER.debug("Valid system IDs for cleanup: %s", valid_system_ids)

    # Clean up any orphan devices (devices with no entities)
    await async_remove_orphan_devices(hass, entry, valid_system_ids)

    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_remove_docker_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove all Docker-related entities and devices for this config entry."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    # First, remove all Docker entities
    entities_to_remove = []
    for entity in entity_registry.entities.values():
        if entity.config_entry_id != entry.entry_id:
            continue

        # Check if this is a Docker entity by unique_id pattern
        if entity.unique_id and "docker_" in entity.unique_id:
            entities_to_remove.append(entity)

    for entity in entities_to_remove:
        _LOGGER.info("Removing Docker entity: %s", entity.entity_id)
        entity_registry.async_remove(entity.entity_id)

    if entities_to_remove:
        _LOGGER.info("Removed %d Docker entities", len(entities_to_remove))

    # Then, remove Docker devices (devices with "docker_" in their identifier)
    devices_to_remove = []
    for device in device_registry.devices.values():
        if entry.entry_id not in device.config_entries:
            continue

        # Check if this is a Docker device by identifier pattern
        for identifier in device.identifiers:
            if len(identifier) >= 2 and identifier[0] == DOMAIN:
                if "docker_" in str(identifier[1]):
                    devices_to_remove.append(device)
                    break

    for device in devices_to_remove:
        _LOGGER.info("Removing Docker device: %s", device.name)
        device_registry.async_remove_device(device.id)

    if devices_to_remove:
        _LOGGER.info("Removed %d Docker devices", len(devices_to_remove))


async def async_remove_orphan_devices(
    hass: HomeAssistant, entry: ConfigEntry, valid_system_ids: set[str] | None = None
) -> None:
    """Remove orphan devices that have no entities or belong to invalid system IDs.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        valid_system_ids: Set of valid system IDs. If provided, devices/entities
                          with identifiers not in this set will be removed.
    """
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    # First, directly remove devices with invalid 8-char hex identifiers
    # These are SMART device IDs that were incorrectly used as system IDs
    if valid_system_ids:
        invalid_devices = []
        for device in device_registry.devices.values():
            if entry.entry_id not in device.config_entries:
                continue

            for identifier in device.identifiers:
                if len(identifier) >= 2 and identifier[0] == DOMAIN:
                    device_id = str(identifier[1])
                    # Check if this is an 8-char hex ID that's not a valid system
                    if (
                        len(device_id) == 8
                        and device_id not in valid_system_ids
                        and all(c in "0123456789abcdef" for c in device_id.lower())
                    ):
                        invalid_devices.append(device)
                        _LOGGER.info(
                            "Found device with invalid system ID: %s (identifier: %s)",
                            device.name, device_id
                        )
                        break

        for device in invalid_devices:
            _LOGGER.info("Removing device with invalid ID: %s", device.name)
            device_registry.async_remove_device(device.id)

        if invalid_devices:
            _LOGGER.info("Removed %d devices with invalid system IDs", len(invalid_devices))

    # Second, remove entities that belong to invalid system IDs
    # This handles the case where binary sensors were created for SMART device IDs
    if valid_system_ids:
        entities_to_remove = []
        for entity in entity_registry.entities.values():
            if entity.config_entry_id != entry.entry_id:
                continue

            # Check if this entity's unique_id starts with an invalid system ID
            # Binary sensors have format: {system_id}_status_v4
            if entity.unique_id:
                # Extract the first part before _status or other suffixes
                parts = entity.unique_id.split("_")
                if parts:
                    potential_system_id = parts[0]
                    # If it looks like a short ID (8 hex chars) and isn't a valid system
                    # and isn't a special prefix like "docker" or "smart"
                    if (
                        len(potential_system_id) == 8
                        and potential_system_id not in valid_system_ids
                        and potential_system_id not in ("docker", "smart")
                        and all(c in "0123456789abcdef" for c in potential_system_id.lower())
                    ):
                        entities_to_remove.append(entity)
                        _LOGGER.debug(
                            "Marking entity for removal (invalid system ID): %s (unique_id: %s)",
                            entity.entity_id, entity.unique_id
                        )

        for entity in entities_to_remove:
            _LOGGER.info("Removing entity with invalid system ID: %s", entity.entity_id)
            entity_registry.async_remove(entity.entity_id)

        if entities_to_remove:
            _LOGGER.info("Removed %d entities with invalid system IDs", len(entities_to_remove))

    # Finally, remove orphan devices (devices with no entities)
    devices_with_entities = set()

    # Find all devices that have at least one entity
    for entity in entity_registry.entities.values():
        if entity.config_entry_id == entry.entry_id and entity.device_id:
            devices_with_entities.add(entity.device_id)

    orphan_devices = []
    for device in device_registry.devices.values():
        if entry.entry_id not in device.config_entries:
            continue

        if device.id not in devices_with_entities:
            orphan_devices.append(device)

    for device in orphan_devices:
        _LOGGER.info("Removing orphan device: %s (%s)", device.name, device.id)
        device_registry.async_remove_device(device.id)

    if orphan_devices:
        _LOGGER.info("Removed %d orphan devices", len(orphan_devices))


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
