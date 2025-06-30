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

# Entity names
SENSOR_TYPES = {
    "cpu": {
        "name": "CPU Usage",
        "unit": "%",
        "icon": "mdi:cpu-64-bit",
        "device_class": None,
    },
    "ram": {
        "name": "Memory Usage",
        "unit": "%",
        "icon": "mdi:memory",
        "device_class": None,
    },
    "disk": {
        "name": "Disk Usage",
        "unit": "%",
        "icon": "mdi:harddisk",
        "device_class": None,
    },
    "network_up": {
        "name": "Network Upload",
        "unit": "MB/s",
        "icon": "mdi:upload-network",
        "device_class": "data_rate",
    },
    "network_down": {
        "name": "Network Download",
        "unit": "MB/s",
        "icon": "mdi:download-network",
        "device_class": "data_rate",
    },
    "temperature": {
        "name": "Temperature",
        "unit": "°C",
        "icon": "mdi:thermometer",
        "device_class": "temperature",
    },
    "uptime": {
        "name": "Uptime",
        "unit": "s",
        "icon": "mdi:clock",
        "device_class": "duration",
    },
}
