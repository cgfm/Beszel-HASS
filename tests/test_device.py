"""Tests for Beszel device grouping and container identity migration."""

import importlib
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
device = importlib.import_module("custom_components.beszel.device")
coordinator_module = importlib.import_module("custom_components.beszel.coordinator")
BeszelDataUpdateCoordinator = coordinator_module.BeszelDataUpdateCoordinator


def container(key: str, record_id: str) -> dict:
    """Return a normalized container record as the coordinator exposes it."""
    return {
        "key": key,
        "id": record_id,
        "system_id": "pc-1",
        "system_name": "Queen",
        "name": "app_epicgamesfree",
    }


class SmartDeviceInfoTests(unittest.TestCase):
    """SMART sensors belong to the monitored system device."""

    def test_smart_device_info_uses_parent_system_identifier(self) -> None:
        coordinator = SimpleNamespace(namespace="hub123")
        disk = {
            "id": "smart-record",
            "system_id": "pc-1",
            "disk_id": "sda",
            "model": "Example SSD",
        }

        device_info = device.smart_device_info(coordinator, disk)

        self.assertEqual(
            device_info["identifiers"],
            {("beszel", "hub123:system:pc-1")},
        )
        self.assertNotIn(
            ("beszel", "hub123:smart:smart-record"),
            device_info["identifiers"],
        )
        self.assertNotIn("via_device", device_info)


class ContainerDeviceInfoTests(unittest.TestCase):
    """A container device is identified by its stable identity."""

    def test_container_device_info_ignores_the_runtime_id(self) -> None:
        coordinator = SimpleNamespace(
            namespace="hub123", api=SimpleNamespace(base_url="http://hub:8090")
        )
        identity = "container-4f2a1c9e77b0"
        device_info = device.container_device_info(
            coordinator, identity, container(identity, "2f8fe5734408")
        )

        self.assertEqual(
            device_info["identifiers"],
            {("beszel", f"hub123:container:{identity}")},
        )
        self.assertNotIn(
            ("beszel", "hub123:container:2f8fe5734408"),
            device_info["identifiers"],
        )


class ContainerIdentityMapTests(unittest.TestCase):
    """Superseded container IDs must map onto the stable identity."""

    def test_runtime_ids_map_to_their_identity(self) -> None:
        identity = "container-4f2a1c9e77b0"
        coordinator = SimpleNamespace(
            namespace="hub123",
            containers={identity: container(identity, "2f8fe5734408")},
        )

        self.assertEqual(
            device.container_identity_map(coordinator),
            {"container:2f8fe5734408": f"container:{identity}"},
        )

    def test_already_migrated_containers_map_to_nothing(self) -> None:
        identity = "container-4f2a1c9e77b0"
        coordinator = SimpleNamespace(
            namespace="hub123",
            containers={identity: container(identity, identity)},
        )

        self.assertEqual(device.container_identity_map(coordinator), {})

    def test_only_the_current_runtime_id_is_known(self) -> None:
        """A device created before a recreate still holds the old runtime ID."""
        identity = "container-4f2a1c9e77b0"
        coordinator = SimpleNamespace(
            namespace="hub123",
            containers={identity: container(identity, "9c1b4a77e120")},
        )

        identities = device.container_identity_map(coordinator)

        self.assertEqual(
            identities, {"container:9c1b4a77e120": f"container:{identity}"}
        )
        self.assertNotIn("container:ae6711c0fa60", identities)

    def test_incomplete_records_are_skipped(self) -> None:
        coordinator = SimpleNamespace(
            namespace="hub123",
            containers={
                "container-a": {"key": "container-a"},
                "container-b": {"key": "container-b", "id": None},
                "container-c": {"key": "container-c", "id": 4711},
            },
        )

        self.assertEqual(device.container_identity_map(coordinator), {})

    def test_duplicate_records_both_map_to_the_stable_identity(self) -> None:
        identity = "container-4f2a1c9e77b0"
        coordinator = SimpleNamespace(
            containers={
                identity: {"id": "new", "record_ids": ["old", "new"]},
            },
        )

        self.assertEqual(
            device.container_identity_map(coordinator),
            {
                "container:old": f"container:{identity}",
                "container:new": f"container:{identity}",
            },
        )


class ContainerRegistryMigrationTests(unittest.IsolatedAsyncioTestCase):
    """Keep registry entries that cannot safely be migrated during setup."""

    async def test_setup_keeps_unmatched_container_entries(self) -> None:
        integration = importlib.import_module("custom_components.beszel")
        namespace = "aaaaaaaaaaaa"
        identity = "container-4f2a1c9e77b0"
        entry = Mock(entry_id="beszel-entry")
        coordinator = Mock(
            namespace=namespace,
            containers={identity: container(identity, "new-runtime-id")},
            systems={},
            smart_devices={},
            async_config_entry_first_refresh=AsyncMock(),
        )
        existing = {
            "sensor.recreated": f"{namespace}:container:old-runtime-id:cpu",
            "sensor.other_hub": "bbbbbbbbbbbb:container:old-runtime-id:cpu",
            "sensor.missing": f"{namespace}:container:container-missing:cpu",
        }
        registry = Mock(
            entities={
                entity_id: SimpleNamespace(
                    entity_id=entity_id,
                    config_entry_id=entry.entry_id,
                    unique_id=unique_id,
                )
                for entity_id, unique_id in existing.items()
            }
        )
        hass = Mock(data={})
        hass.config_entries.async_forward_entry_setups = AsyncMock()

        with (
            patch.object(
                integration, "BeszelDataUpdateCoordinator", return_value=coordinator
            ),
            patch.object(integration, "async_migrate_container_devices"),
            patch.object(integration, "async_remove_empty_devices"),
            patch.object(device.er, "async_get", return_value=registry),
        ):
            for complete in (False, True):
                with self.subTest(complete=complete):
                    coordinator.data = {"complete": {"containers": complete}}
                    self.assertTrue(await integration.async_setup_entry(hass, entry))

        registry.async_update_entity.assert_not_called()
        registry.async_remove.assert_not_called()

    def test_migrate_matching_entry_without_deleting_it_on_collision(self) -> None:
        identity = "container-4f2a1c9e77b0"
        entry = SimpleNamespace(entry_id="beszel-entry")
        coordinator = SimpleNamespace(
            namespace="aaaaaaaaaaaa",
            containers={identity: container(identity, "live")},
            systems={},
            smart_devices={},
        )
        entity = SimpleNamespace(
            entity_id="sensor.user_named_cpu",
            config_entry_id=entry.entry_id,
            unique_id="aaaaaaaaaaaa:container:live:cpu",
        )
        registry = Mock(entities={entity.entity_id: entity})
        registry.async_get_entity_id.return_value = None

        with patch.object(device.er, "async_get", return_value=registry):
            device.async_migrate_legacy_entities(None, entry, coordinator)
            registry.async_update_entity.assert_called_once_with(
                entity.entity_id, new_unique_id=f"aaaaaaaaaaaa:container:{identity}:cpu"
            )

            registry.async_update_entity.reset_mock()
            registry.async_get_entity_id.return_value = "sensor.existing_cpu"
            registry.async_get.return_value = SimpleNamespace(
                config_entry_id=entry.entry_id
            )
            device.async_migrate_legacy_entities(None, entry, coordinator)

        registry.async_update_entity.assert_not_called()
        registry.async_remove.assert_not_called()


class ContainerInventoryMergeTests(unittest.TestCase):
    """A recreated container must not leave a second entity or device behind."""

    def setUp(self) -> None:
        coordinator = BeszelDataUpdateCoordinator.__new__(BeszelDataUpdateCoordinator)
        coordinator._cache = {
            "systems": {},
            "containers": {"container-x": container("container-x", "old123")},
            "smart": {},
        }
        coordinator._misses = {"systems": {}, "containers": {}, "smart": {}}
        self.coordinator = coordinator

    def test_fresh_record_replaces_the_stale_one_under_one_identity(self) -> None:
        merged = self.coordinator._merge_inventory(
            "containers",
            {"container-x": container("container-x", "new456")},
            True,
        )

        self.assertEqual(list(merged), ["container-x"])
        self.assertEqual(merged["container-x"]["id"], "new456")

    def test_absent_container_is_retired_after_the_stale_limit(self) -> None:
        for _ in range(3):
            merged = self.coordinator._merge_inventory("containers", {}, True)

        self.assertEqual(merged, {})


class TemperatureMigrationTests(unittest.TestCase):
    """Individual temperature sensors keep their identity on endpoint changes."""

    def test_migrate_observed_sensor_and_keep_unobserved_sensor(self) -> None:
        old_coordinator = SimpleNamespace(namespace="aaaaaaaaaaaa")
        coordinator = SimpleNamespace(
            namespace="bbbbbbbbbbbb",
            systems={"pc-1": {"temperatures": {"cpu:package": 42.0}}},
            containers={},
            smart_devices={},
        )
        entry = SimpleNamespace(entry_id="beszel-entry")
        entities = {}
        for name, entity_id in (
            ("cpu:package", "sensor.user_named_cpu"),
            ("gpu", "sensor.user_named_gpu"),
        ):
            entities[entity_id] = SimpleNamespace(
                entity_id=entity_id,
                config_entry_id=entry.entry_id,
                unique_id=device.entity_unique_id(
                    old_coordinator, "temperature", f"pc-1:{name}", "value"
                ),
            )
        registry = Mock(entities=entities)
        registry.async_get_entity_id.return_value = None

        with patch.object(device.er, "async_get", return_value=registry):
            device.async_migrate_legacy_entities(None, entry, coordinator)

        registry.async_update_entity.assert_called_once_with(
            "sensor.user_named_cpu",
            new_unique_id="bbbbbbbbbbbb:temperature:pc-1:cpu:package:value",
        )
        registry.async_remove.assert_not_called()


if __name__ == "__main__":
    unittest.main()
