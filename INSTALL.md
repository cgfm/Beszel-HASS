# Installation Guide - Beszel Home Assistant Integration

This guide provides detailed installation instructions for the Beszel Home Assistant integration.

## Prerequisites

- Home Assistant 2023.1.0 or newer
- A running [Beszel](https://github.com/henrygd/beszel) instance
- Valid Beszel user credentials (admin or user with systems access)
- Network connectivity between Home Assistant and Beszel server

## Installation Methods

### Method 1: HACS (Recommended)

The easiest way to install this integration is through HACS (Home Assistant Community Store).

#### First-time HACS Setup

If you haven't installed HACS yet:

1. Install HACS following the [official guide](https://hacs.xyz/docs/setup/download)
2. Add the HACS integration to Home Assistant
3. Restart Home Assistant

#### Installing the Integration

1. Open Home Assistant
2. Navigate to **HACS** > **Integrations**
3. Click the **⋮** menu (three dots) in the top right
4. Select **Custom repositories**
5. Add repository:
   - **Repository**: `https://github.com/cgfm/beszel-hass`
   - **Type**: Integration
6. Click **ADD**
7. Search for "**Beszel**" in HACS
8. Click **DOWNLOAD**
9. **Restart Home Assistant**

### Method 2: Manual Installation

For manual installation or development:

1. Download the latest release from [GitHub releases](https://github.com/cgfm/beszel-hass/releases)
2. Extract the ZIP file
3. Copy the `custom_components/beszel` folder to your Home Assistant `config/custom_components/` directory
4. Your directory structure should look like:
   ```
   config/
   ├── custom_components/
   │   └── beszel/
   │       ├── __init__.py
   │       ├── manifest.json
   │       ├── config_flow.py
   │       └── ... (other files)
   └── configuration.yaml
   ```
5. Restart Home Assistant

### Method 3: Git Clone (Development)

For development or latest features:

```bash
cd /config/custom_components/
git clone https://github.com/cgfm/beszel-hass.git beszel
```

Then restart Home Assistant.

## Configuration

### Adding the Integration

1. Navigate to **Settings** > **Devices & Services**
2. Click **+ ADD INTEGRATION**
3. Search for "**Beszel**"
4. Click on the Beszel integration

### Configuration Parameters

Fill in the following details:

| Parameter | Description | Example | Required |
|-----------|-------------|---------|----------|
| **Host** | Beszel server hostname or IP | `localhost` or `192.168.1.100` | ✅ |
| **Port** | Beszel server port | `8090` (default) | ✅ |
| **Username** | Beszel username | `admin` | ✅ |
| **Password** | Beszel password | `your_password` | ✅ |
| **Use SSL** | Enable HTTPS connection | ☑️ if using HTTPS | ❌ |
| **Monitor Docker Containers** | Enable Docker container monitoring | ☑️ to monitor containers | ❌ |

### Example Configurations

#### Local Beszel Server
- **Host**: `localhost` or `127.0.0.1`
- **Port**: `8090`
- **SSL**: Disabled

#### Remote Beszel Server (HTTP)
- **Host**: `beszel.example.com`
- **Port**: `8090`
- **SSL**: Disabled

#### Remote Beszel Server (HTTPS)
- **Host**: `beszel.example.com`
- **Port**: `443` or `8090`
- **SSL**: Enabled

### Testing the Configuration

The integration will automatically:
1. Test connection to your Beszel server
2. Authenticate with provided credentials
3. Discover all monitored systems
4. Create devices and entities

If successful, you'll see:
- A confirmation message
- New devices in **Settings** > **Devices & Services** > **Beszel**

## Post-Installation

### Verify Installation

1. Check **Settings** > **Devices & Services** > **Beszel**
2. You should see:
   - Integration listed as configured
   - One device per monitored system
   - Additional devices for Docker containers (if enabled)
   - Multiple entities per device (CPU, Memory, Disk, etc.)

### View Entities

1. Navigate to **Settings** > **Devices & Services** > **Entities**
2. Filter by "beszel" to see all entities
3. Or go to **Developer Tools** > **States** and search for `sensor.beszel_`

### Entity Types

The integration creates the following entity types:

#### System Entities (Always Present)
- `sensor.{system_name}_cpu_usage` - CPU usage percentage
- `sensor.{system_name}_memory_usage` - Memory usage percentage
- `sensor.{system_name}_disk_usage` - Disk usage percentage
- `sensor.{system_name}_network_up` - Network upload speed
- `sensor.{system_name}_network_down` - Network download speed
- `sensor.{system_name}_uptime` - System uptime
- `binary_sensor.{system_name}_status` - System online/offline status

#### Docker Entities (When Docker Monitoring Enabled)
- `sensor.docker_{container_name}_cpu_usage` - Container CPU usage percentage
- `sensor.docker_{container_name}_memory_usage` - Container memory usage percentage
- `sensor.docker_{container_name}_memory_bytes` - Container memory usage in bytes
- `sensor.docker_{container_name}_network_rx` - Container network received bytes
- `sensor.docker_{container_name}_network_tx` - Container network transmitted bytes
- `binary_sensor.docker_{container_name}_status` - Container running/stopped status

### Dashboard Integration

Add Beszel entities to your dashboard:

1. Edit a dashboard
2. Add cards for Beszel sensors
3. Suggested cards:
   - **Gauge Card** for CPU/Memory/Disk usage
   - **History Graph** for usage over time
   - **Entity Card** for system status
   - **Glance Card** for Docker container overview (if enabled)

## Troubleshooting

### Common Issues

#### "Cannot connect" Error
- **Check network connectivity**: Can Home Assistant reach your Beszel server?
- **Verify host/port**: Ensure correct hostname and port
- **Check firewall**: Make sure Beszel port is accessible
- **Test manually**: Try accessing `http://YOUR_HOST:PORT` in a browser

#### "Authentication failed" Error
- **Verify credentials**: Double-check username and password
- **User permissions**: Ensure user has access to view systems in Beszel
- **API access**: Confirm PocketBase API is enabled in Beszel

#### "No systems found" Error
- **Systems configured**: Ensure you have systems configured in Beszel
- **Systems active**: Verify systems are actively reporting to Beszel
- **User access**: Check if your user can see systems in Beszel web interface

#### SSL/HTTPS Issues
- **Certificate validation**: For self-signed certificates, you may need to configure Home Assistant to accept them
- **Mixed content**: Don't mix HTTP and HTTPS settings

### Debug Logging

Enable debug logging for detailed troubleshooting:

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.beszel: debug
```

Then restart Home Assistant and check **Settings** > **System** > **Logs**.

### Manual Testing

Test the integration independently:

```bash
# Navigate to integration directory
cd /config/custom_components/beszel/

# Run test script (if available)
python test_simple.py YOUR_HOST YOUR_PORT cgfm YOUR_PASSWORD
```

## Uninstallation

### Remove Integration

1. Navigate to **Settings** > **Devices & Services**
2. Find the **Beszel** integration
3. Click **⋮** (three dots) > **Delete**
4. Confirm deletion

### Remove Files (Manual Installation)

If manually installed, also remove the files:

```bash
rm -rf /config/custom_components/beszel/
```

Then restart Home Assistant.

### Remove HACS Installation

If installed via HACS:

1. Go to **HACS** > **Integrations**
2. Find **Beszel** integration
3. Click **⋮** > **Remove**

## Support

- **Documentation**: Check this guide and the main [README](README.md)
- **Issues**: [Report bugs](https://github.com/cgfm/beszel-hass/issues)
- **Discussions**: [Ask questions](https://github.com/cgfm/beszel-hass/discussions)
- **Beszel Support**: [Beszel documentation](https://github.com/henrygd/beszel)
