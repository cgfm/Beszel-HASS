# Beszel Home Assistant Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]

**Diese Integration wird über HACS bereitgestellt.**

Eine Home Assistant Integration für [Beszel](https://github.com/henrygd/beszel) - ein leichtgewichtiges Server-Monitoring-Tool.

## Features

- Überwachung von Server-Metriken (CPU, RAM, Disk, Network)
- Automatische Erkennung aller überwachten Server
- Konfiguration über die Home Assistant UI
- Unterstützung für mehrere Beszel-Instanzen

## Installation

### HACS (Empfohlen)

1. Öffnen Sie HACS in Home Assistant
2. Klicken Sie auf "Integrations"
3. Klicken Sie auf die drei Punkte in der oberen rechten Ecke
4. Wählen Sie "Custom repositories"
5. Fügen Sie die URL dieses Repositories hinzu: `https://github.com/cgfm/beszel-hass`
6. Wählen Sie "Integration" als Kategorie
7. Klicken Sie auf "Add"
8. Suchen Sie nach "Beszel" und installieren Sie es
9. Starten Sie Home Assistant neu

### Manuelle Installation

1. Kopieren Sie den `beszel` Ordner in Ihr `config/custom_components/` Verzeichnis
2. Starten Sie Home Assistant neu

## Konfiguration

1. Gehen Sie zu "Einstellungen" > "Geräte & Dienste"
2. Klicken Sie auf "+ Integration hinzufügen"
3. Suchen Sie nach "Beszel"
4. Geben Sie die URL Ihrer Beszel-Instanz und Ihre Zugangsdaten ein

## Supported Entities

### Sensoren
- CPU-Auslastung (%)
- RAM-Auslastung (%)
- Disk-Auslastung (%)
- Netzwerk-Upload (MB/s)
- Netzwerk-Download (MB/s)
- System-Temperatur (°C)
- Uptime

### Binary Sensoren
- Server-Status (Online/Offline)

## Beitragen

Beiträge sind willkommen! Bitte lesen Sie [CONTRIBUTING.md](CONTRIBUTING.md) für Details.

## License

Diese Integration steht unter der [MIT License](LICENSE).

[releases-shield]: https://img.shields.io/github/release/YOURUSERNAME/beszel-hass.svg?style=for-the-badge
[releases]: https://github.com/YOURUSERNAME/beszel-hass/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/YOURUSERNAME/beszel-hass.svg?style=for-the-badge
[commits]: https://github.com/YOURUSERNAME/beszel-hass/commits/main
[license-shield]: https://img.shields.io/github/license/YOURUSERNAME/beszel-hass.svg?style=for-the-badge
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[maintenance-shield]: https://img.shields.io/badge/maintainer-YOURNAME-blue.svg?style=for-the-badge
[user_profile]: https://github.com/YOURUSERNAME
