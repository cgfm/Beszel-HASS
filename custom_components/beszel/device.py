"""Device registry and entity management for Beszel integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN


@callback
def async_remove_stale_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    current_systems: list[str],
) -> None:
    """Remove entities for systems that no longer exist."""
    entity_registry = er.async_get(hass)

    # Get all entities for this integration
    entities = {
        entity.unique_id: entity
        for entity in entity_registry.entities.values()
        if entity.config_entry_id == entry.entry_id
    }

    # Remove entities for systems that no longer exist
    for unique_id, entity in entities.items():
        system_id = unique_id.split("_")[0]  # Extract system_id from unique_id
        if system_id not in current_systems:
            entity_registry.async_remove(entity.entity_id)


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
