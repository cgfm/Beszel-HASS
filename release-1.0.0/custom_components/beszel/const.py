"""Constants for the Beszel integration."""

from typing import Final

DOMAIN: Final = "beszel"

# Configuration
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_SSL: Final = "use_ssl"

# Defaults
DEFAULT_PORT: Final = 8090
DEFAULT_SSL: Final = False
DEFAULT_SCAN_INTERVAL: Final = 30

# API endpoints
API_SYSTEMS: Final = "/api/systems"
API_STATS: Final = "/api/systems/{system_id}/stats"

# Entity names and mapping for Beszel PocketBase data
SENSOR_TYPES = {
    "cpu": {
        "name": "CPU Usage",
        "unit": "%",
        "icon": "mdi:cpu-64-bit",
        "device_class": None,
        "info_key": "cpu",  # maps to info.cpu in system record
    },
    "memory": {
        "name": "Memory Usage",
        "unit": "%",
        "icon": "mdi:memory",
        "device_class": None,
        "info_key": "mp",  # maps to info.mp (memory percentage)
    },
    "disk": {
        "name": "Disk Usage",
        "unit": "%",
        "icon": "mdi:harddisk",
        "device_class": None,
        "info_key": "dp",  # maps to info.dp (disk percentage)
    },
    "disk_temp": {
        "name": "Disk Temperature",
        "unit": "°C",
        "icon": "mdi:thermometer",
        "device_class": "temperature",
        "info_key": "dt",  # maps to info.dt (disk temperature)
    },
    "uptime": {
        "name": "Uptime",
        "unit": "s",
        "icon": "mdi:clock",
        "device_class": "duration",
        "info_key": "u",  # maps to info.u (uptime in seconds)
    },
    "bandwidth": {
        "name": "Bandwidth Usage",
        "unit": "B",
        "icon": "mdi:chart-line",
        "device_class": "data_size",
        "info_key": "b",  # maps to info.b (bandwidth)
    },
}
