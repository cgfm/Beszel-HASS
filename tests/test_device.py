"""Tests for Beszel device grouping and container identity migration."""

import importlib
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

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

    def test_known_segments_cover_current_and_superseded_ids(self) -> None:
        """The sweep must keep every identity that can still own entities."""
        identity = "container-4f2a1c9e77b0"
        legacy = "legacy-9f5c1a2b3c4d"
        coordinator = SimpleNamespace(
            namespace="hub123",
            containers={
                identity: {"key": identity, "id": "9c1b4a77e120"},
                legacy: {"key": legacy, "id": legacy},
            },
        )

        segments = device.container_identity_segments(coordinator)

        self.assertEqual(
            segments,
            {
                f"container:{identity}",
                f"container:{legacy}",
                "container:9c1b4a77e120",
            },
        )


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


if __name__ == "__main__":
    unittest.main()
