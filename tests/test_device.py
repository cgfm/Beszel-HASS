"""Tests for Beszel device grouping."""

import importlib
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
device = importlib.import_module("custom_components.beszel.device")
smart_device_info = device.smart_device_info


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

        device_info = smart_device_info(coordinator, disk)

        self.assertEqual(
            device_info["identifiers"],
            {("beszel", "hub123:system:pc-1")},
        )
        self.assertNotIn(
            ("beszel", "hub123:smart:smart-record"),
            device_info["identifiers"],
        )
        self.assertNotIn("via_device", device_info)


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
