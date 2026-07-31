# Beszel Home Assistant Integration

[![GitHub Release][releases-shield]][releases]
[![HACS Custom][hacsbadge]][hacs]
[![License][license-shield]](LICENSE)

This custom integration exposes systems, containers, extra filesystems, and SMART
disks from a [Beszel](https://github.com/henrygd/beszel) Hub in Home Assistant.

## Highlights

- Local polling through Beszel's PocketBase API
- Automatic discovery of new systems, containers, filesystems, and SMART disks
- Current and legacy Beszel metric formats normalized to correct Home Assistant units
- Real container running state on current Beszel versions
- Pagination for installations with more than one PocketBase page of records
- Automatic token refresh and a Home Assistant reauthentication flow
- Configurable update interval from 10 to 3600 seconds
- English and German config-flow and entity translations
- Stable, hub-scoped entity and device identifiers

## Requirements

- Home Assistant 2024.12.0 or newer
- A Beszel Hub reachable from Home Assistant
- A Beszel user with permission to read the monitored systems
- Password login enabled for that user; OAuth-only Beszel accounts cannot currently be
  used by this integration

The integration stores the configured credentials in Home Assistant's config entry.
HTTP sends those credentials and the session token without transport encryption. Use
HTTPS whenever traffic leaves a trusted local network.

## Installation

### HACS

1. In HACS, open **Integrations** and select **Custom repositories**.
2. Add `https://github.com/cgfm/beszel-hass` as an **Integration** repository.
3. Install **Beszel** and restart Home Assistant.

### Manual

Copy `custom_components/beszel` into `<config>/custom_components/beszel`, then
restart Home Assistant. See [INSTALLATION.md](INSTALLATION.md) for more detail.

## Configuration

Go to **Settings → Devices & services → Add integration → Beszel**.

| Field | Meaning | Default |
| --- | --- | --- |
| Host | Hostname or IP only; no scheme, port, or path | — |
| Port | Beszel Hub port | `8090` |
| Use HTTPS | Connect using TLS | Off |
| Email or username / password | Beszel user credentials | — |
| Monitor containers | Discover Docker and Podman containers | On |
| Update interval | Polling interval in seconds (`10`–`3600`) | `30` |

The exact same HTTPS/host/port endpoint can only be configured once. Different
Beszel Hubs remain separate even if their internal PocketBase record IDs happen to
match.

## Entities and units

System devices expose CPU, memory, disk, load, GPU, battery, temperature, uptime,
bandwidth, disk I/O, network I/O, memory/swap sizes, IP address, and connectivity
where Beszel supplies the value. Extra filesystems add usage, size, and I/O sensors
to their corresponding system device. SMART records add health, temperature, sector
counts, and power-on hours to that same system device.

Container devices expose:

| Sensor | Native unit |
| --- | --- |
| CPU usage | `%` |
| Memory usage | `MB` |
| Network sent / received | `B/s` |
| Running status | Binary sensor |

System disk/network rates and bandwidth are also exposed as `B/s`. Legacy Beszel
rate fields are converted with Beszel's 1024² factor; new byte fields are used
directly. Disk and memory capacities remain in GB, matching Beszel's API.

Inventory is not deleted after a single failed or incomplete poll. A record must be
absent from three complete inventory updates before its exact entities are retired.

## Troubleshooting

Enable debug logging temporarily:

```yaml
logger:
  logs:
    custom_components.beszel: debug
```

Common checks:

- Confirm `http(s)://HOST:PORT/api/health` is reachable from Home Assistant.
- Confirm the user can see the systems in the Beszel UI.
- Match the HTTPS option to the Hub or reverse proxy.
- If password authentication was disabled in Beszel, enable it for a dedicated
  integration user.

## Development

```bash
python -m pip install -r requirements_dev.txt
for file in custom_components/beszel/*.py tests/*.py create_release.py; do black --workers 1 --check "$file"; done
isort --check-only custom_components/beszel/*.py tests/*.py create_release.py
pytest -v
```

The release archive is created with `python create_release.py`. Release changes are
listed in [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).

[releases-shield]: https://img.shields.io/github/release/cgfm/beszel-hass.svg?style=for-the-badge
[releases]: https://github.com/cgfm/beszel-hass/releases
[license-shield]: https://img.shields.io/github/license/cgfm/beszel-hass.svg?style=for-the-badge
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
