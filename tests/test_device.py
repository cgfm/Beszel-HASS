"""Tests for Beszel device grouping."""

from types import SimpleNamespace
import unittest

from custom_components.beszel.device import smart_device_info


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


if __name__ == "__main__":
    unittest.main()
