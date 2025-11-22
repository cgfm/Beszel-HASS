"""Device registry and entity management for Beszel integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def build_unique_id_prefixes(coordinator_data: dict[str, Any]) -> set[str]:
    """Build set of unique ID prefixes from coordinator data.

    This generates all possible unique ID prefixes that should exist based on
    the current coordinator data, accounting for different entity unique ID formats.

    Args:
        coordinator_data: The coordinator.data dict containing system and container info

    Returns:
        Set of unique ID prefixes that should exist
    """
    prefixes = set()

    for system_data in coordinator_data.values():
        if "system_info" not in system_data:
            continue

        system_info = system_data["system_info"]
        system_id = system_info.get("id")
        data_type = system_data.get("type", "system")

        if not system_id:
            continue

        if data_type == "docker":
            # Docker containers have two different unique ID formats:
            # Binary sensors: "docker_{container_id}_status_v4"
            prefixes.add(f"docker_{system_id}")

            # Regular sensors: "{system_prefix}_docker_{container_id}_{sensor_type}_v5"
            # We need to sanitize the system_name to match what sensors.py does
            system_name = system_info.get("system_name", "Unknown System")
            system_prefix = (
                system_name.lower()
                .replace(" ", "_")
                .replace("(", "")
                .replace(")", "")
                .replace("-", "_")
            )
            prefixes.add(f"{system_prefix}_docker_{system_id}")
        else:
            # Regular systems use: "{system_id}_{sensor_type}_v4"
            prefixes.add(system_id)

    _LOGGER.debug("Built unique ID prefixes: %s", prefixes)
    return prefixes


@callback
def async_remove_stale_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    current_unique_id_prefixes: set[str],
) -> None:
    """Remove entities for systems/containers that no longer exist.

    Args:
        hass: Home Assistant instance
        entry: Config entry for this integration
        current_unique_id_prefixes: Set of unique ID prefixes for currently existing entities.
            For regular systems: the system_id itself (e.g., "abc123")
            For Docker containers: "docker_{container_id}" (e.g., "docker_nginx_system1")
    """
    entity_registry = er.async_get(hass)

    # Get all entities for this integration
    entities_to_check = [
        entity
        for entity in entity_registry.entities.values()
        if entity.config_entry_id == entry.entry_id
    ]

    _LOGGER.debug(
        "Checking %d entities for staleness (current prefixes: %s)",
        len(entities_to_check),
        current_unique_id_prefixes,
    )

    removed_count = 0

    # Remove entities whose system/container no longer exists
    for entity in entities_to_check:
        if entity.unique_id is None:
            continue

        # Extract the system/container identifier from the unique_id
        # Formats:
        #   Regular system: "{system_id}_{sensor_type}_v4"
        #   Docker (binary): "docker_{container_id}_status_v4"
        #   Docker (sensor): "{system_prefix}_docker_{container_id}_{sensor_type}_v5"

        should_remove = True

        # Check if this unique_id matches any current system/container
        for prefix in current_unique_id_prefixes:
            if entity.unique_id.startswith(f"{prefix}_"):
                should_remove = False
                break

        if should_remove:
            _LOGGER.info(
                "Removing stale entity: %s (unique_id: %s)",
                entity.entity_id,
                entity.unique_id,
            )
            entity_registry.async_remove(entity.entity_id)
            removed_count += 1

    if removed_count > 0:
        _LOGGER.info("Removed %d stale entities", removed_count)
    else:
        _LOGGER.debug("No stale entities found")


@callback
def async_get_device_info(system_id: str, system_info: dict) -> dict:
    """Get device information for a system."""
    return {
        "identifiers": {(DOMAIN, system_id)},
        "name": system_info.get("name", f"System {system_id}"),
        "manufacturer": "Beszel",
        "model": "Server Monitor",
        "sw_version": system_info.get("version"),
        "configuration_url": None,  # Could be set to Beszel web interface
    }
