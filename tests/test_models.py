"""Tests for Beszel payload normalization without a Home Assistant runtime."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

MODULE_PATH = Path(__file__).parents[1] / "custom_components" / "beszel" / "models.py"
SPEC = importlib.util.spec_from_file_location("beszel_models", MODULE_PATH)
assert SPEC and SPEC.loader
models = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = models
SPEC.loader.exec_module(models)


class HostNormalizationTests(unittest.TestCase):
    """Endpoint identity must be canonical and unambiguous."""

    def test_host_and_ipv6_normalization(self) -> None:
        self.assertEqual(models.normalize_host("Example.COM."), "example.com")
        self.assertEqual(models.normalize_host("[2001:0db8::1]"), "2001:db8::1")
        self.assertEqual(
            models.hub_unique_id("2001:db8::1", 8090, True),
            "https://[2001:db8::1]:8090",
        )

    def test_rejects_urls_and_paths(self) -> None:
        for value in ("https://beszel.local", "beszel.local/api", "user@host"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                models.normalize_host(value)


class SystemNormalizationTests(unittest.TestCase):
    """Current and legacy Beszel fields must yield identical native units."""

    def test_current_fields_and_array_values(self) -> None:
        system = {
            "id": "system123",
            "name": "Server",
            "host": "10.0.0.2",
            "status": "up",
            "info": {
                "u": 1234,
                "cpu": 10,
                "mp": 20,
                "dp": 30,
                "bb": 3210,
                "dt": 44.4,
                "bat": [87, 1],
                "g": 23.5,
            },
        }
        stats = {
            "cpu": 11.2,
            "m": 16,
            "mu": 8,
            "mp": 50,
            "d": 100,
            "du": 20,
            "dp": 20,
            "b": [123, 456],
            "dio": [789, 1011],
            "la": [0.1, 0.2, 0.3],
            "efs": {"media": {"d": 10, "du": 0, "rb": 25, "wb": 50}},
        }
        normalized = models.normalize_system(
            system,
            stats,
            {"cores": 8, "memory": 16 * 1024**3},
        )
        metrics = normalized["metrics"]
        self.assertEqual(metrics["cpu_cores"], 8)
        self.assertEqual(metrics["temperature"], 44.4)
        self.assertEqual(metrics["battery"], 87)
        self.assertEqual(metrics["network_sent"], 123)
        self.assertEqual(metrics["network_received"], 456)
        self.assertEqual(metrics["disk_read"], 789)
        self.assertEqual(metrics["bandwidth"], 3210)
        self.assertEqual(normalized["filesystems"]["media"]["usage"], 0)

    def test_legacy_rates_use_beszel_binary_conversion(self) -> None:
        system = {
            "id": "system123",
            "info": {"b": 1.5, "u": 10, "dt": 0},
        }
        stats = {"ns": 2, "nr": 3.5, "dr": 4, "dw": 5}
        metrics = models.normalize_system(
            system,
            stats,
            {"cores": 4, "memory": 8 * 1024**3},
        )["metrics"]
        self.assertEqual(metrics["cpu_cores"], 4)
        self.assertEqual(metrics["memory_total"], 8)
        self.assertEqual(metrics["bandwidth"], 1_572_864)
        self.assertEqual(metrics["network_sent"], 2_097_152)
        self.assertEqual(metrics["network_received"], 3_670_016)
        self.assertEqual(metrics["disk_read"], 4_194_304)
        self.assertEqual(metrics["disk_write"], 5_242_880)

    def test_omitted_zero_rates_remain_available(self) -> None:
        system = {"id": "system123", "info": {"bb": 0}}
        stats = {
            "cpu": 0,
            "g": {"gpu0": {"n": "GPU"}},
            "efs": {"media": {"d": 10, "du": 0}},
        }
        normalized = models.normalize_system(system, stats)
        metrics = normalized["metrics"]
        self.assertEqual(metrics["network_sent"], 0)
        self.assertEqual(metrics["network_received"], 0)
        self.assertEqual(metrics["disk_read"], 0)
        self.assertEqual(metrics["disk_write"], 0)
        self.assertEqual(metrics["gpu"], 0)
        self.assertEqual(normalized["filesystems"]["media"]["read"], 0)
        self.assertEqual(normalized["filesystems"]["media"]["write"], 0)


class ContainerAndSmartNormalizationTests(unittest.TestCase):
    """Container identity/status and SMART attributes are preserved."""

    def test_current_container_id_status_and_metrics(self) -> None:
        containers = models.normalize_containers(
            [
                {
                    "id": "abc123",
                    "system": "system123",
                    "name": "nginx",
                    "status": "Up 3 hours (healthy)",
                    "memory": 12.5,
                }
            ],
            [
                {
                    "system": "system123",
                    "stats": [{"n": "nginx", "c": 3.2, "m": 12.5, "b": [8, 9]}],
                }
            ],
            {"system123": "Server"},
        )
        container = containers["abc123"]
        self.assertTrue(container["running"])
        self.assertEqual(container["metrics"]["memory"], 12.5)
        self.assertEqual(container["metrics"]["network_sent"], 8)
        self.assertEqual(container["metrics"]["network_received"], 9)

    def test_legacy_container_gets_collision_resistant_id(self) -> None:
        containers = models.normalize_containers(
            [],
            [{"system": "sys", "stats": [{"n": "web", "ns": 1, "nr": 2}]}],
            {"sys": "Server"},
        )
        container_id, container = next(iter(containers.items()))
        self.assertTrue(container_id.startswith("legacy-"))
        self.assertEqual(container["metrics"]["network_sent"], 1_048_576)
        self.assertEqual(container["metrics"]["network_received"], 2_097_152)

    def test_live_mode_and_stale_history_do_not_create_ghosts(self) -> None:
        historical = [
            {
                "system": "sys",
                "created": "2026-07-31T10:00:00Z",
                "stats": [{"n": "stopped", "c": 1}],
            }
        ]
        self.assertEqual(
            models.normalize_containers(
                [], historical, {"sys": "Server"}, include_historical_only=False
            ),
            {},
        )
        self.assertEqual(
            models.normalize_containers(
                [],
                historical,
                {"sys": "Server"},
                system_stats_created={"sys": "2026-07-31T10:05:00Z"},
            ),
            {},
        )

    def test_smart_attribute_mapping(self) -> None:
        disk = models.normalize_smart(
            {
                "id": "diskrecord",
                "system": "sys",
                "name": "sda",
                "state": "passed",
                "temp": 35,
                "hours": 456,
                "cycles": 12,
                "attributes": [
                    {"id": 5, "rv": 2, "raw": 999},
                    {"id": 9, "rv": "123"},
                    {"id": 197, "rv": None, "raw": 3},
                ],
            },
            {"sys": "Server"},
        )
        assert disk is not None
        self.assertEqual(disk["disk_id"], "sda")
        self.assertEqual(disk["metrics"]["reallocated_sectors"], 2)
        self.assertEqual(disk["metrics"]["pending_sectors"], 3)
        self.assertEqual(disk["metrics"]["power_on_hours"], 456)
        self.assertEqual(disk["power_cycles"], 12)


if __name__ == "__main__":
    unittest.main()
