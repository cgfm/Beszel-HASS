"""Constants for the Beszel integration."""

from typing import Final

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTemperature,
    UnitOfTime,
)

DOMAIN: Final = "beszel"

# Configuration
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_SSL: Final = "use_ssl"
CONF_INCLUDE_DOCKER: Final = "include_docker"

# Defaults
DEFAULT_PORT: Final = 8090
DEFAULT_SSL: Final = False
DEFAULT_INCLUDE_DOCKER: Final = True
DEFAULT_SCAN_INTERVAL: Final = 30

# API endpoints
API_SYSTEMS: Final = "/api/systems"
API_STATS: Final = "/api/systems/{system_id}/stats"

# Entity names and mapping for Beszel PocketBase data
# Fields can come from two sources:
# - "info" object: mostly static system information
# - "stats" object: performance metrics that change frequently
# Some field names (like 'm') exist in BOTH but mean different things!

SENSOR_TYPES = {
    "cpu": {
        "name": "CPU Usage",
        "unit": "%",
        "icon": "mdi:cpu-64-bit",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "info_key": "cpu",  # maps to info.cpu in system record
        "data_source": "info",  # Read from info object
    },
    "memory": {
        "name": "Memory Usage",
        "unit": "%",
        "icon": "mdi:memory",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "info_key": "mp",  # maps to info.mp (memory percentage)
        "data_source": "info",
    },
    "disk": {
        "name": "Disk Usage",
        "unit": "%",
        "icon": "mdi:harddisk",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "info_key": "dp",  # maps to info.dp (disk percentage)
        "data_source": "info",
    },
    "disk_temp": {
        "name": "Disk Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "info_key": "dt",  # maps to info.dt (disk temperature)
        "data_source": "info",
    },
    "uptime": {
        "name": "Uptime",
        "unit": UnitOfTime.SECONDS,
        "icon": "mdi:clock",
        "device_class": SensorDeviceClass.DURATION,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "info_key": "u",  # maps to info.u (uptime in seconds)
        "data_source": "info",
    },
    "bandwidth": {
        "name": "Bandwidth Usage",
        "unit": UnitOfInformation.BYTES,
        "icon": "mdi:chart-line",
        "device_class": SensorDeviceClass.DATA_SIZE,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "info_key": "b",  # maps to info.b (bandwidth)
        "data_source": "info",
    },
    "load_1": {
        "name": "Load Average (1m)",
        "unit": None,
        "icon": "mdi:speedometer",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "info_key": "la",  # maps to stats.la array [1m, 5m, 15m]
        "data_source": "stats",
        "array_index": 0,  # First element is 1m load
    },
    "load_5": {
        "name": "Load Average (5m)",
        "unit": None,
        "icon": "mdi:speedometer",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "info_key": "la",  # maps to stats.la array [1m, 5m, 15m]
        "data_source": "stats",
        "array_index": 1,  # Second element is 5m load
    },
    "load_15": {
        "name": "Load Average (15m)",
        "unit": None,
        "icon": "mdi:speedometer",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "info_key": "la",  # maps to stats.la array [1m, 5m, 15m]
        "data_source": "stats",
        "array_index": 2,  # Third element is 15m load
    },
    "gpu": {
        "name": "GPU Usage",
        "unit": "%",
        "icon": "mdi:expansion-card",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "info_key": "g",  # maps to info.g (gpu usage percentage)
        "data_source": "info",
    },
    "battery": {
        "name": "Battery",
        "unit": "%",
        "icon": "mdi:battery",
        "device_class": SensorDeviceClass.BATTERY,
        "state_class": SensorStateClass.MEASUREMENT,
        "info_key": "bat",  # maps to stats.bat (battery percentage)
        "data_source": "stats",  # Battery data is in system_stats, not info
    },
    "disk_read": {
        "name": "Disk Read Rate",
        "unit": UnitOfDataRate.BYTES_PER_SECOND,
        "icon": "mdi:arrow-down-bold",
        "device_class": SensorDeviceClass.DATA_RATE,
        "state_class": SensorStateClass.MEASUREMENT,
        "info_key": "dr",  # maps to stats.dr (disk read per second)
        "data_source": "stats",
    },
    "disk_write": {
        "name": "Disk Write Rate",
        "unit": UnitOfDataRate.BYTES_PER_SECOND,
        "icon": "mdi:arrow-up-bold",
        "device_class": SensorDeviceClass.DATA_RATE,
        "state_class": SensorStateClass.MEASUREMENT,
        "info_key": "dw",  # maps to stats.dw (disk write per second)
        "data_source": "stats",
    },
    "network_sent": {
        "name": "Network Sent",
        "unit": UnitOfDataRate.BYTES_PER_SECOND,
        "icon": "mdi:upload-network",
        "device_class": SensorDeviceClass.DATA_RATE,
        "state_class": SensorStateClass.MEASUREMENT,
        "info_key": "ns",  # maps to stats.ns (network bytes sent)
        "data_source": "stats",
    },
    "network_recv": {
        "name": "Network Received",
        "unit": UnitOfDataRate.BYTES_PER_SECOND,
        "icon": "mdi:download-network",
        "device_class": SensorDeviceClass.DATA_RATE,
        "state_class": SensorStateClass.MEASUREMENT,
        "info_key": "nr",  # maps to stats.nr (network bytes received)
        "data_source": "stats",
    },
    "memory_used": {
        "name": "Memory Used",
        "unit": UnitOfInformation.GIGABYTES,
        "icon": "mdi:memory",
        "device_class": SensorDeviceClass.DATA_SIZE,
        "state_class": SensorStateClass.MEASUREMENT,
        "info_key": "mu",  # maps to stats.mu (memory used in GB from API)
        "data_source": "stats",
    },
    "memory_total": {
        "name": "Memory Total",
        "unit": UnitOfInformation.GIGABYTES,
        "icon": "mdi:memory",
        "device_class": SensorDeviceClass.DATA_SIZE,
        "state_class": SensorStateClass.MEASUREMENT,
        "info_key": "m",  # maps to stats.m (total memory in GB from API)
        "data_source": "stats",
    },
    "swap_used": {
        "name": "Swap Used",
        "unit": UnitOfInformation.GIGABYTES,
        "icon": "mdi:swap-horizontal",
        "device_class": SensorDeviceClass.DATA_SIZE,
        "state_class": SensorStateClass.MEASUREMENT,
        "info_key": "su",  # maps to stats.su (swap used in GB from API)
        "data_source": "stats",
    },
    "swap_total": {
        "name": "Swap Total",
        "unit": UnitOfInformation.GIGABYTES,
        "icon": "mdi:swap-horizontal",
        "device_class": SensorDeviceClass.DATA_SIZE,
        "state_class": SensorStateClass.MEASUREMENT,
        "info_key": "s",  # maps to stats.s (total swap in GB from API)
        "data_source": "stats",
    },
}

# Docker container sensor types
DOCKER_SENSOR_TYPES = {
    "docker_cpu": {
        "name": "CPU Usage",
        "unit": "%",
        "icon": "mdi:docker",
        "device_class": None,
        "state_class": "measurement",
    },
    "docker_memory_bytes": {
        "name": "Memory Usage",
        "unit": UnitOfInformation.BYTES,
        "icon": "mdi:memory",
        "device_class": SensorDeviceClass.DATA_SIZE,
        "state_class": "measurement",
    },
    "docker_network_rx": {
        "name": "Network RX",
        "unit": UnitOfDataRate.BYTES_PER_SECOND,
        "icon": "mdi:download",
        "device_class": SensorDeviceClass.DATA_RATE,
        "state_class": "measurement",
    },
    "docker_network_tx": {
        "name": "Network TX",
        "unit": UnitOfDataRate.BYTES_PER_SECOND,
        "icon": "mdi:upload",
        "device_class": SensorDeviceClass.DATA_RATE,
        "state_class": "measurement",
    },
}

# SMART disk sensor types - enabled by default
# These sensors expose S.M.A.R.T. health data for physical disks
SMART_SENSOR_TYPES = {
    "health": {
        "name": "SMART Health",
        "icon": "mdi:harddisk-check",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "key": "state",
        "enabled_default": True,
    },
    "temperature": {
        "name": "Disk Temperature",
        "icon": "mdi:thermometer",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "key": "temp",
        "enabled_default": True,
    },
    "reallocated_sectors": {
        "name": "Reallocated Sectors",
        "icon": "mdi:harddisk-remove",
        "device_class": None,
        "state_class": SensorStateClass.TOTAL,
        "unit": None,
        "key": "attr_5",
        "attr_id": 5,
        "enabled_default": True,
    },
    "pending_sectors": {
        "name": "Pending Sectors",
        "icon": "mdi:harddisk-plus",
        "device_class": None,
        "state_class": SensorStateClass.TOTAL,
        "unit": None,
        "key": "attr_197",
        "attr_id": 197,
        "enabled_default": True,
    },
    "uncorrectable_sectors": {
        "name": "Uncorrectable Sectors",
        "icon": "mdi:harddisk-remove",
        "device_class": None,
        "state_class": SensorStateClass.TOTAL,
        "unit": None,
        "key": "attr_198",
        "attr_id": 198,
        "enabled_default": True,
    },
    "power_on_hours": {
        "name": "Power On Hours",
        "icon": "mdi:clock-outline",
        "device_class": SensorDeviceClass.DURATION,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfTime.HOURS,
        "key": "attr_9",
        "attr_id": 9,
        "enabled_default": True,
    },
}
