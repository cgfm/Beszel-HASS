"""The Beszel integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SSL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SSL,
    DOMAIN,
)
from .coordinator import BeszelDataUpdateCoordinator
from .device import (
    async_migrate_legacy_entities,
    async_remove_docker_entities,
    async_remove_empty_devices,
)
from .models import hub_unique_id, normalize_host

PLATFORMS = (Platform.SENSOR, Platform.BINARY_SENSOR)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate pre-1.2 entries to normalized endpoint settings."""
    if entry.version > 2:
        return False
    if entry.version == 2:
        return True
    data = dict(entry.data)
    try:
        data[CONF_HOST] = normalize_host(data[CONF_HOST])
    except (KeyError, ValueError):
        return False
    data.setdefault(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    try:
        port = int(data.get(CONF_PORT, DEFAULT_PORT))
    except (TypeError, ValueError):
        return False
    if not 1 <= port <= 65535:
        return False
    use_ssl = bool(data.get(CONF_SSL, DEFAULT_SSL))
    data[CONF_PORT] = port
    data[CONF_SSL] = use_ssl
    unique_id = hub_unique_id(data[CONF_HOST], port, use_ssl)
    if any(
        other.entry_id != entry.entry_id and other.unique_id == unique_id
        for other in hass.config_entries.async_entries(DOMAIN)
    ):
        return False
    hass.config_entries.async_update_entry(
        entry,
        data=data,
        unique_id=unique_id,
        version=2,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Beszel from a config entry."""
    coordinator = BeszelDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    async_migrate_legacy_entities(hass, entry, coordinator)
    if not coordinator.is_docker_enabled():
        async_remove_docker_entities(hass, entry, coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_remove_empty_devices(hass, entry)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    hass.data[DOMAIN].pop(entry.entry_id, None)
    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload Beszel when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
