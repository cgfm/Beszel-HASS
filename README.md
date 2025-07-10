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

- 🖥️ **Server Monitoring**: Monitor CPU, RAM, disk usage, temperature, and network stats
- 🐳 **Docker Container Monitoring**: Complete monitoring of Docker containers with auto-discovery
- 🔄 **Auto Discovery**: Automatically discovers all monitored servers from your Beszel instance
- ⚙️ **Easy Setup**: Configure through Home Assistant UI with config flow
- 🏠 **Native Integration**: Full Home Assistant integration with devices and entities
- 📊 **Real-time Data**: Live updates of system metrics with user-friendly units
- 🔌 **Multiple Instances**: Support for multiple Beszel instances
- 🌐 **SSL Support**: Secure connections to your Beszel server
- 📱 **Mobile Friendly**: Optimized display units (MB, GB, MB/s) for better mobile experience

## Supported Entities

### System Sensors
- **CPU Usage** (%) - Current CPU utilization
- **Memory Usage** (%) - Current RAM utilization
- **Disk Usage** (%) - Current disk space utilization
- **Disk Temperature** (°C) - Disk temperature (if available)
- **Uptime** (seconds) - System uptime with duration device class
- **Bandwidth** (bytes) - Network bandwidth usage with data size device class

### Docker Container Sensors
When Docker monitoring is enabled, each container gets:
- **CPU Usage** (%) - Container CPU utilization
- **Memory Usage** (bytes) - Container memory usage with automatic unit formatting (MB/GB)
- **Network RX** (bytes/s) - Network received with automatic rate formatting (MB/s, GB/s)
- **Network TX** (bytes/s) - Network transmitted with automatic rate formatting (MB/s, GB/s)

### Binary Sensors
- **System Status** - Online/Offline status of monitored systems
- **Docker Container Status** - Running/Stopped status of Docker containers

All entities use Home Assistant's native device classes for optimal display and automatic unit conversion (kB, MB, GB, etc.).

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots menu (⋮) in the top right
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/cgfm/beszel-hass`
6. Select "Integration" as the category
7. Click "Add"
8. Search for "Beszel" and install it
9. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/cgfm/beszel-hass/releases)
2. Extract the files
3. Copy the `custom_components/beszel` folder to your Home Assistant `config/custom_components/` directory
4. Restart Home Assistant

## Configuration

### Initial Setup

1. Go to "Settings" > "Devices & Services" in Home Assistant
2. Click "+ Add Integration"
3. Search for "Beszel"
4. Enter your Beszel server details:

#### Configuration Options

| Field | Description | Default | Required |
|-------|-------------|---------|----------|
| **Host** | Your Beszel server hostname or IP address | - | ✅ |
| **Port** | Port number of your Beszel instance | 8090 | ✅ |
| **Username** | Your Beszel username | - | ✅ |
| **Password** | Your Beszel password | - | ✅ |
| **Use SSL** | Enable if using HTTPS connection | False | ❌ |
| **Monitor Docker Containers** | Include Docker container monitoring | True | ❌ |

#### Example Configuration

```
Host: 192.168.1.100
Port: 8090
Username: admin
Password: your_secure_password
Use SSL: ☐ (unchecked for HTTP)
Monitor Docker Containers: ☑ (checked to include Docker monitoring)
```

### Advanced Configuration

The integration supports multiple Beszel instances. Simply add multiple integrations with different connection details.

### Environment Variables (Development)

For development and testing, you can use environment variables:

```bash
BESZEL_HOST=192.168.1.100
BESZEL_PORT=8090
BESZEL_USER=admin
BESZEL_PASSWORD=your_password
BESZEL_SSL=false
```

## Entity Naming Convention

Entities are automatically named with descriptive names:

### System Entities
- `sensor.server_name_cpu_usage`
- `sensor.server_name_memory_usage`
- `binary_sensor.server_name_status`

### Docker Container Entities
- `sensor.docker_container_name_system_name_cpu_usage`
- `sensor.docker_container_name_system_name_memory_usage`
- `binary_sensor.docker_container_name_system_name_status`

Example: `sensor.docker_vaultwarden_homeserver_memory_usage`

## Device Classes and Units

The integration uses Home Assistant's native device classes for optimal display:

| Sensor Type | Device Class | Unit | Auto-Formatting |
|-------------|--------------|------|----------------|
| CPU Usage | - | % | No |
| Memory Usage | `data_size` | bytes | Yes (MB, GB) |
| Disk Usage | - | % | No |
| Disk Temperature | `temperature` | °C | No |
| Network RX/TX | `data_rate` | bytes/s | Yes (MB/s, GB/s) |
| Uptime | `duration` | seconds | Yes (days, hours) |
| Bandwidth | `data_size` | bytes | Yes (MB, GB) |

## Requirements

- **Home Assistant**: 2023.1.0 or newer
- **Beszel Server**: Latest version with PocketBase API enabled
- **Python**: 3.10+ (handled by Home Assistant)
- **Network Access**: Home Assistant must be able to reach your Beszel instance

### Beszel Server Requirements

Your Beszel instance should be:
- Running and accessible from Home Assistant
- Configured with at least one monitored system
- Have valid user credentials for API access

## Troubleshooting

### Common Issues

#### Authentication Failed
```
Error: Failed to authenticate with Beszel server
```

**Solutions:**
- Verify your Beszel username and password
- Check if your Beszel instance is accessible via the configured host/port
- Ensure the PocketBase API is enabled and running
- Test connection manually: `http://your-host:8090/api/health`

#### No Systems Found
```
Warning: No systems found in Beszel instance
```

**Solutions:**
- Ensure you have systems configured and running in Beszel
- Check if systems are actively reporting data (green status in Beszel UI)
- Verify your user account has permission to view systems
- Wait a few minutes for systems to report initial data

#### Connection Issues
```
Error: Unable to connect to Beszel server
```

**Solutions:**
- Check host and port settings
- Verify SSL settings match your Beszel setup (HTTP vs HTTPS)
- Ensure your Beszel instance is running and accessible
- Check firewall settings on both Home Assistant and Beszel server
- Test network connectivity: `ping your-beszel-host`

#### Docker Containers Not Showing
```
Info: Docker monitoring enabled but no containers found
```

**Solutions:**
- Ensure Docker containers are configured in Beszel
- Check if Docker monitoring is enabled in your Beszel agent
- Verify containers are running and reporting to Beszel
- Disable and re-enable Docker monitoring in the integration settings

### Debug Logging

To enable detailed debug logging for troubleshooting:

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.beszel: debug
    custom_components.beszel.api: debug
    custom_components.beszel.coordinator: debug
```

After adding this configuration:
1. Restart Home Assistant
2. Go to "Settings" > "System" > "Logs"
3. Look for `custom_components.beszel` entries

### Performance Considerations

- **Update Interval**: Default is 30 seconds, configurable in integration options
- **API Rate Limiting**: The integration respects Beszel's API limits
- **Memory Usage**: Minimal impact, typically <10MB additional RAM usage
- **Network Traffic**: ~1-5KB per update per monitored system

## API Compatibility

This integration is compatible with:
- **Beszel**: v0.1.0 and newer
- **PocketBase**: v0.16.0 and newer (included with Beszel)

## Development

### Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/cgfm/beszel-hass.git
   cd beszel-hass
   ```

2. **Install development dependencies:**
   ```bash
   pip install -r requirements_dev.txt
   ```

3. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

4. **Set up test environment:**
   ```bash
   # Copy and edit environment file
   cp .env.example .env
   # Edit .env with your test Beszel instance details
   ```

5. **Development workflow:**
   ```bash
   # Make your changes
   # Run linting
   black custom_components/beszel/
   pylint custom_components/beszel/

   # Test your changes
   # Submit a pull request
   ```

### Code Quality

This project uses:
- **Black** for code formatting
- **Pylint** for code analysis
- **MyPy** for type checking
- **Pre-commit** hooks for automated checks

### Testing

The integration includes comprehensive testing:
- Unit tests for all components
- Integration tests with mock Beszel server
- Automated testing via GitHub Actions

## Support

### Getting Help

- 🐛 **Bug Reports**: [Open an issue](https://github.com/cgfm/beszel-hass/issues/new?template=bug_report.md)
- 💡 **Feature Requests**: [Request a feature](https://github.com/cgfm/beszel-hass/issues/new?template=feature_request.md)
- ❓ **Questions**: [Start a discussion](https://github.com/cgfm/beszel-hass/discussions)
- 📖 **Beszel Server Issues**: [Beszel documentation](https://github.com/henrygd/beszel)

### Community

- [Home Assistant Community Forum](https://community.home-assistant.io/)
- [HACS Discord](https://discord.gg/apgchf8)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed list of changes and releases.

## Roadmap

- [ ] Historical data charts
- [ ] Alert thresholds and notifications
- [ ] System health monitoring
- [ ] Performance optimization dashboard
- [ ] Custom sensor configurations

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **[Beszel](https://github.com/henrygd/beszel)** by henrygd - Excellent lightweight server monitoring
- **Home Assistant Community** - Framework and integration patterns
- **HACS** - Making custom integrations accessible
- **Contributors** - Everyone who helps improve this integration

---

**Star this repository** ⭐ if you find it useful!

[releases-shield]: https://img.shields.io/github/release/cgfm/beszel-hass.svg?style=for-the-badge
[releases]: https://github.com/cgfm/beszel-hass/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/cgfm/beszel-hass.svg?style=for-the-badge
[commits]: https://github.com/cgfm/beszel-hass/commits/main
[license-shield]: https://img.shields.io/github/license/cgfm/beszel-hass.svg?style=for-the-badge
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[maintenance-shield]: https://img.shields.io/badge/maintainer-cgfm-blue.svg?style=for-the-badge
[user_profile]: https://github.com/cgfm
