# Beszel Home Assistant Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]

**This integration can be installed through HACS.**

A Home Assistant integration for [Beszel](https://github.com/henrygd/beszel) - a lightweight server monitoring tool built with PocketBase.

![Beszel Dashboard](https://github.com/henrygd/beszel/raw/main/readme-image.png)

## Features

- 🖥️ **Server Monitoring**: Monitor CPU, RAM, disk usage and network stats
- 🔄 **Auto Discovery**: Automatically discovers all monitored servers from your Beszel instance
- ⚙️ **Easy Setup**: Configure through Home Assistant UI with config flow
- 🏠 **Native Integration**: Full Home Assistant integration with devices and entities
- 📊 **Real-time Data**: Live updates of system metrics
- 🔌 **Multiple Instances**: Support for multiple Beszel instances
- 🌐 **SSL Support**: Secure connections to your Beszel server

## Supported Entities

### Sensors
- **CPU Usage** (%) - Current CPU utilization
- **Memory Usage** (%) - Current RAM utilization  
- **Disk Usage** (%) - Current disk space utilization
- **Bandwidth Up** (MB/s) - Network upload speed
- **Bandwidth Down** (MB/s) - Network download speed
- **Uptime** - System uptime in seconds

### Binary Sensors
- **System Status** - Online/Offline status of monitored systems

Each monitored system appears as a separate device in Home Assistant with all its metrics grouped together.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/cgfm/beszel-hass`
6. Select "Integration" as category
7. Click "Add"
8. Search for "Beszel" and install it
9. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/beszel` folder to your `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to "Settings" > "Devices & Services"
2. Click "+ Add Integration"
3. Search for "Beszel"
4. Enter your Beszel server details:
   - **Host**: Your Beszel server hostname/IP
   - **Port**: Port number (default: 8090)
   - **Username**: Your Beszel username
   - **Password**: Your Beszel password
   - **Use SSL**: Enable if using HTTPS

## Requirements

- Home Assistant 2023.1.0 or newer
- A running [Beszel](https://github.com/henrygd/beszel) instance
- Valid Beszel user credentials

## Troubleshooting

### Common Issues

**Authentication Failed**
- Verify your Beszel username and password
- Check if your Beszel instance is accessible
- Ensure the PocketBase API is enabled

**No Systems Found**
- Make sure you have systems configured in Beszel
- Check if systems are actively reporting data
- Verify your user has access to view systems

**Connection Issues**
- Check host and port settings
- Verify SSL settings match your Beszel setup
- Ensure your Beszel instance is running and accessible

### Debug Logging

To enable debug logging for this integration:

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.beszel: debug
```

## Development

### Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

### Development Setup

1. Clone this repository
2. Install development dependencies: `pip install -r requirements_dev.txt`
3. Run pre-commit hooks: `pre-commit install`
4. Make your changes
5. Run tests: `pytest`
6. Submit a pull request

## Support

- [Open an issue](https://github.com/cgfm/beszel-hass/issues) for bug reports
- [Start a discussion](https://github.com/cgfm/beszel-hass/discussions) for questions
- Check the [Beszel documentation](https://github.com/henrygd/beszel) for server-side issues

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Beszel](https://github.com/henrygd/beszel) by henrygd for the excellent monitoring tool
- Home Assistant community for the integration framework
- HACS for making custom integrations easy to install

---

[releases-shield]: https://img.shields.io/github/release/cgfm/beszel-hass.svg?style=for-the-badge
[releases]: https://github.com/cgfm/beszel-hass/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/cgfm/beszel-hass.svg?style=for-the-badge
[commits]: https://github.com/cgfm/beszel-hass/commits/main
[license-shield]: https://img.shields.io/github/license/cgfm/beszel-hass.svg?style=for-the-badge
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[maintenance-shield]: https://img.shields.io/badge/maintainer-cgfm-blue.svg?style=for-the-badge
[user_profile]: https://github.com/cgfm
