"""Data update coordinator for Beszel."""

from __future__ import annotations

from datetime import timedelta
from hashlib import sha256
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BeszelAPIClient, BeszelAPIError, BeszelAuthError
from .const import (
    CONF_HOST,
    CONF_INCLUDE_DOCKER,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SSL,
    CONF_USERNAME,
    DEFAULT_INCLUDE_DOCKER,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SSL,
    DOMAIN,
    STALE_UPDATE_LIMIT,
)
from .models import normalize_containers, normalize_smart, normalize_system

_LOGGER = logging.getLogger(__name__)
CoordinatorData = dict[str, dict[str, dict[str, Any]] | dict[str, bool]]


class BeszelDataUpdateCoordinator(DataUpdateCoordinator[CoordinatorData]):
    """Fetch, normalize, and safely age Beszel inventory."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.include_docker = entry.data.get(
            CONF_INCLUDE_DOCKER, DEFAULT_INCLUDE_DOCKER
        )
        self.api = BeszelAPIClient(
            session=async_get_clientsession(hass),
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            use_ssl=entry.data.get(CONF_SSL, DEFAULT_SSL),
        )
        self.namespace = sha256(self.api.base_url.encode()).hexdigest()[:12]
        self._cache: dict[str, dict[str, dict[str, Any]]] = {
            "systems": {},
            "containers": {},
            "smart": {},
        }
        self._misses: dict[str, dict[str, int]] = {
            "systems": {},
            "containers": {},
            "smart": {},
        }
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(
                seconds=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )

    async def _async_update_data(self) -> CoordinatorData:
        try:
            snapshot = await self.api.get_snapshot(include_docker=self.include_docker)
        except BeszelAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except BeszelAPIError as err:
            raise UpdateFailed(f"Error communicating with Beszel: {err}") from err

        old_systems = self._cache["systems"]
        systems: dict[str, dict[str, Any]] = {}
        system_names: dict[str, str] = {}
        for record in snapshot.systems:
            system_id = record.get("id")
            if not isinstance(system_id, str) or not system_id:
                continue
            stats = snapshot.system_stats.get(system_id)
            if stats is None and not snapshot.complete["system_stats"]:
                old = old_systems.get(system_id, {})
                old_stats = old.get("raw_stats")
                stats = old_stats if isinstance(old_stats, dict) else {}
            details = snapshot.system_details.get(system_id)
            if details is None and not snapshot.complete["system_details"]:
                old = old_systems.get(system_id, {})
                old_details = old.get("raw_details")
                details = old_details if isinstance(old_details, dict) else {}
            normalized = normalize_system(record, stats or {}, details or {})
            systems[system_id] = normalized
            system_names[system_id] = normalized["name"]

        systems = self._merge_inventory("systems", systems, complete=True)
        system_names.update(
            {system_id: data["name"] for system_id, data in systems.items()}
        )

        if self.include_docker:
            containers = normalize_containers(
                snapshot.containers,
                snapshot.container_stats,
                system_names,
                system_stats_created=snapshot.system_stats_created,
                include_historical_only=snapshot.container_mode == "legacy",
            )
            if not snapshot.complete["container_stats"]:
                containers = self._restore_container_rates(containers)
            containers = self._merge_inventory(
                "containers", containers, snapshot.complete["containers"]
            )
            containers = self._drop_orphans("containers", containers, systems)
        else:
            self._cache["containers"] = {}
            self._misses["containers"] = {}
            containers = {}

        smart: dict[str, dict[str, Any]] = {}
        for record in snapshot.smart_devices:
            normalized = normalize_smart(record, system_names)
            if normalized is not None:
                smart[normalized["id"]] = normalized
        smart = self._merge_inventory("smart", smart, snapshot.complete["smart"])
        smart = self._drop_orphans("smart", smart, systems)

        return {
            "systems": systems,
            "containers": containers,
            "smart": smart,
            "complete": snapshot.complete,
        }

    def _merge_inventory(
        self,
        kind: str,
        fresh: dict[str, dict[str, Any]],
        complete: bool,
    ) -> dict[str, dict[str, Any]]:
        """Keep old records through incomplete or transiently empty updates."""
        previous = self._cache[kind]
        misses = self._misses[kind]
        merged = dict(previous)
        merged.update(fresh)
        for record_id in fresh:
            misses.pop(record_id, None)

        if complete:
            for record_id in set(previous) - set(fresh):
                misses[record_id] = misses.get(record_id, 0) + 1
                if misses[record_id] >= STALE_UPDATE_LIMIT:
                    merged.pop(record_id, None)
                    misses.pop(record_id, None)
                else:
                    stale = dict(previous[record_id])
                    stale["stale"] = True
                    if kind == "systems":
                        stale["status"] = "unknown"
                    elif kind == "containers":
                        stale["status"] = "missing"
                        stale["running"] = False
                    merged[record_id] = stale
        else:
            for record_id in set(previous) - set(fresh):
                stale = dict(previous[record_id])
                stale["stale"] = True
                merged[record_id] = stale

        self._cache[kind] = merged
        return merged

    def _drop_orphans(
        self,
        kind: str,
        records: dict[str, dict[str, Any]],
        systems: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Remove child records once their parent system is confirmed gone."""
        filtered = {
            record_id: record
            for record_id, record in records.items()
            if record.get("system_id") in systems
        }
        for record_id in set(records) - set(filtered):
            self._misses[kind].pop(record_id, None)
        self._cache[kind] = filtered
        return filtered

    def _restore_container_rates(
        self, containers: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Retain directional rates if only container history failed."""
        previous = self._cache["containers"]
        for container_id, container in containers.items():
            old = previous.get(container_id)
            if not old:
                continue
            metrics = dict(container.get("metrics", {}))
            old_metrics = old.get("metrics", {})
            for key in ("network_sent", "network_received"):
                if metrics.get(key) is None:
                    metrics[key] = old_metrics.get(key)
            container["metrics"] = metrics
        return containers

    @property
    def systems(self) -> dict[str, dict[str, Any]]:
        return self._section("systems")

    @property
    def containers(self) -> dict[str, dict[str, Any]]:
        return self._section("containers")

    @property
    def smart_devices(self) -> dict[str, dict[str, Any]]:
        return self._section("smart")

    def _section(self, name: str) -> dict[str, dict[str, Any]]:
        if not self.data:
            return {}
        section = self.data.get(name)
        return section if isinstance(section, dict) else {}

    def get_system_data(self, system_id: str) -> dict[str, Any] | None:
        return self.systems.get(system_id)

    def get_docker_data(self, container_id: str) -> dict[str, Any] | None:
        return self.containers.get(container_id)

    def get_smart_data(self, smart_id: str) -> dict[str, Any] | None:
        return self.smart_devices.get(smart_id)

    def is_docker_enabled(self) -> bool:
        return self.include_docker
