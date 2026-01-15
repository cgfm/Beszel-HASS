"""String constants for Beszel integration."""

STRINGS = {
    "de": {
        "config_flow": {
            "title": "Beszel Konfiguration",
            "description": "Konfigurieren Sie Ihre Beszel-Instanz",
            "host": "Host/IP-Adresse",
            "port": "Port",
            "use_ssl": "SSL verwenden",
            "username": "Benutzername",
            "password": "Passwort",
            "include_docker": "Docker-Container überwachen",
            "cannot_connect": (
                "Verbindung fehlgeschlagen. Überprüfen Sie Host und Port."
            ),
            "invalid_auth": (
                "Ungültige Anmeldedaten. " "Überprüfen Sie Benutzername und Passwort."
            ),
            "unknown": "Ein unbekannter Fehler ist aufgetreten.",
        },
        "entities": {
            "ip_address": "IP-Adresse",
            "cpu_usage": "CPU-Auslastung",
            "memory_usage": "Arbeitsspeicher-Auslastung",
            "disk_usage": "Festplatten-Auslastung",
            "network_upload": "Netzwerk Upload",
            "network_download": "Netzwerk Download",
            "temperature": "Temperatur",
            "uptime": "Betriebszeit",
            "status": "Status",
            "smart_health": "SMART Gesundheit",
            "smart_temperature": "Festplatten-Temperatur",
            "smart_reallocated_sectors": "Neu zugewiesene Sektoren",
            "smart_pending_sectors": "Ausstehende Sektoren",
            "smart_uncorrectable_sectors": "Nicht korrigierbare Sektoren",
            "smart_power_on_hours": "Betriebsstunden",
        },
    },
    "en": {
        "config_flow": {
            "title": "Beszel Configuration",
            "description": "Configure your Beszel instance",
            "host": "Host/IP Address",
            "port": "Port",
            "use_ssl": "Use SSL",
            "username": "Username",
            "password": "Password",
            "cannot_connect": "Failed to connect. Check host and port.",
            "invalid_auth": "Invalid credentials. Check username and password.",
            "unknown": "An unknown error occurred.",
        },
        "entities": {
            "ip_address": "IP Address",
            "cpu_usage": "CPU Usage",
            "memory_usage": "Memory Usage",
            "disk_usage": "Disk Usage",
            "network_upload": "Network Upload",
            "network_download": "Network Download",
            "temperature": "Temperature",
            "uptime": "Uptime",
            "status": "Status",
            "smart_health": "SMART Health",
            "smart_temperature": "Disk Temperature",
            "smart_reallocated_sectors": "Reallocated Sectors",
            "smart_pending_sectors": "Pending Sectors",
            "smart_uncorrectable_sectors": "Uncorrectable Sectors",
            "smart_power_on_hours": "Power On Hours",
        },
    },
}
