# Installation Guide

This comprehensive guide will help you install and configure the Beszel Home Assistant Integration.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Advanced Setup](#advanced-setup)

## Prerequisites

### Home Assistant Requirements

- **Home Assistant**: Version 2023.1.0 or newer
- **Installation Type**: Any (Core, Supervised, Container, OS)
- **Network Access**: Home Assistant must be able to reach your Beszel instance

### Beszel Server Requirements

Before installing this integration, ensure you have:

1. **Running Beszel Instance**
   - Beszel server installed and running
   - At least one monitored system configured
   - PocketBase API accessible (default port 8090)

2. **Valid Credentials**
   - Beszel username and password
   - User account with access to view systems

3. **Network Configuration**
   - Beszel instance accessible from Home Assistant
   - Firewall allowing connections on Beszel port (usually 8090)

### Testing Connectivity

Before proceeding, test the connection to your Beszel instance:

```bash
# Test basic connectivity
curl http://YOUR_BESZEL_HOST:8090/api/health

# Test authentication (replace with your credentials)
curl -X POST http://YOUR_BESZEL_HOST:8090/api/collections/users/auth-with-password \
  -H "Content-Type: application/json" \
  -d '{\"identity\":\"your_username\",\"password\":\"your_password\"}'
```

## Installation Methods

### Method 1: HACS (Recommended)

HACS (Home Assistant Community Store) is the easiest way to install and maintain this integration.

#### Step 1: Install HACS

If you don't have HACS installed:
1. Follow the [HACS installation guide](https://hacs.xyz/docs/setup/download)
2. Restart Home Assistant
3. Complete HACS setup

#### Step 2: Add Custom Repository

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots menu (⋮) in the top right
4. Select "Custom repositories"
5. Add repository URL: `https://github.com/cgfm/beszel-hass`
6. Select "Integration" as the category
7. Click "Add"

#### Step 3: Install Integration

1. In HACS, search for "Beszel"
2. Click on the Beszel integration
3. Click "Install"
4. Restart Home Assistant when prompted

### Method 2: Manual Installation

If you prefer manual installation or don't use HACS:

#### Step 1: Download Files

1. Go to [GitHub Releases](https://github.com/cgfm/beszel-hass/releases)
2. Download the latest release ZIP file
3. Extract the files

#### Step 2: Copy Files

1. Navigate to your Home Assistant configuration directory
2. Create `custom_components` folder if it doesn't exist:
   ```
   config/
   ├── custom_components/  ← Create this if missing
   ├── configuration.yaml
   └── ...
   ```

3. Copy the `beszel` folder to `custom_components`:
   ```
   config/
   ├── custom_components/
   │   └── beszel/  ← Copy this entire folder
   │       ├── __init__.py
   │       ├── manifest.json
   │       ├── config_flow.py
   │       └── ...
   ├── configuration.yaml
   └── ...
   ```

#### Step 3: Restart Home Assistant

Restart Home Assistant to load the new integration.

## Configuration

### Step 1: Add Integration

1. Navigate to "Settings" > "Devices & Services"
2. Click the "+ Add Integration" button
3. Search for "Beszel"
4. Click on the Beszel integration

### Step 2: Enter Connection Details

Fill in the configuration form:

| Field | Description | Example |
|-------|-------------|---------|
| **Host** | Beszel server hostname or IP | `192.168.1.100` or `beszel.local` |
| **Port** | Beszel server port | `8090` |
| **Username** | Your Beszel username | `admin` |
| **Password** | Your Beszel password | `your_secure_password` |
| **Use SSL** | Check if using HTTPS | Usually unchecked for local instances |
| **Monitor Docker Containers** | Include Docker monitoring | Recommended: checked |

### Step 3: Complete Setup

1. Click "Submit"
2. Wait for the integration to connect and discover systems
3. The integration will create devices for each discovered system

## Verification

### Check Devices and Entities

1. Go to "Settings" > "Devices & Services"
2. Click on "Beszel" integration
3. Verify you see:
   - Device for each monitored system
   - Device for each Docker container (if enabled)
   - Multiple sensors per device

### Example Entities

After successful setup, you should see entities like:

**System Entities:**
- `sensor.homeserver_cpu_usage`
- `sensor.homeserver_memory_usage`
- `sensor.homeserver_disk_usage`
- `binary_sensor.homeserver_status`

**Docker Container Entities (if enabled):**
- `sensor.docker_vaultwarden_homeserver_cpu_usage`
- `sensor.docker_vaultwarden_homeserver_memory_usage`
- `binary_sensor.docker_vaultwarden_homeserver_status`

### Test Data Flow

1. Check sensor values in the "States" developer tool
2. Verify values update every 30 seconds (default interval)
3. Confirm binary sensors show correct online/offline status

## Troubleshooting

### Common Installation Issues

#### Integration Not Found

**Problem:** "Beszel" doesn't appear in the integration list

**Solutions:**
1. Ensure Home Assistant was restarted after installation
2. Check that files are in correct location: `custom_components/beszel/`
3. Verify `manifest.json` exists and is valid
4. Check Home Assistant logs for errors

#### Authentication Failed

**Problem:** "Invalid credentials" error during setup

**Solutions:**
1. Verify username and password are correct
2. Test credentials in Beszel web interface
3. Ensure PocketBase API is enabled
4. Check network connectivity to Beszel instance

#### No Systems Discovered

**Problem:** Integration connects but finds no systems

**Solutions:**
1. Verify systems are configured in Beszel
2. Check systems are reporting data (green status in Beszel UI)
3. Ensure user account has permission to view systems
4. Wait a few minutes for initial data collection

### Network Issues

#### Connection Timeout

**Problem:** Integration fails to connect to Beszel

**Solutions:**
1. Verify host and port settings
2. Test network connectivity: `ping YOUR_BESZEL_HOST`
3. Check firewall settings on both ends
4. Ensure Beszel service is running

#### SSL/TLS Issues

**Problem:** SSL connection errors

**Solutions:**
1. Verify SSL checkbox matches your Beszel setup
2. For local instances, usually use HTTP (uncheck SSL)
3. For remote instances with certificates, enable SSL
4. Check certificate validity if using HTTPS

### Debug Mode

Enable detailed logging for troubleshooting:

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.beszel: debug
    custom_components.beszel.api: debug
    custom_components.beszel.coordinator: debug
```

After adding this:
1. Restart Home Assistant
2. Reproduce the issue
3. Check "Settings" > "System" > "Logs" for detailed information

## Advanced Setup

### Multiple Beszel Instances

To monitor multiple Beszel servers:

1. Complete the setup for your first instance
2. Go back to "Settings" > "Devices & Services"
3. Click "+ Add Integration" again
4. Search for "Beszel" and add another instance
5. Configure with different connection details

Each instance will create separate devices and entities.

### Custom Update Intervals

To change the update frequency:

1. Go to "Settings" > "Devices & Services"
2. Click on the Beszel integration
3. Click "Configure"
4. Adjust the scan interval (default: 30 seconds)

**Note:** Very short intervals may impact performance.

### Selective Monitoring

To disable Docker monitoring:

1. During initial setup, uncheck "Monitor Docker Containers"
2. Or reconfigure existing integration:
   - Go to integration settings
   - Click "Configure"
   - Toggle Docker monitoring

### Home Assistant Automations

Example automation using Beszel sensors:

```yaml
# configuration.yaml or automations.yaml
automation:
  - alias: "High CPU Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.homeserver_cpu_usage
      above: 80
    action:
      service: notify.notify
      data:
        message: "Home server CPU usage is high: {{ trigger.to_state.state }}%"
```

### Lovelace Dashboard

Example dashboard card:

```yaml
type: entities
title: Server Monitoring
entities:
  - entity: sensor.homeserver_cpu_usage
    name: CPU Usage
  - entity: sensor.homeserver_memory_usage
    name: Memory Usage
  - entity: sensor.homeserver_disk_usage
    name: Disk Usage
  - entity: binary_sensor.homeserver_status
    name: Status
```

## Security Considerations

### Credentials Management

- Use strong passwords for Beszel accounts
- Consider creating a dedicated Home Assistant user in Beszel
- Regularly rotate passwords

### Network Security

- Use HTTPS when possible for remote Beszel instances
- Consider VPN for external connections
- Implement firewall rules to restrict access

### Home Assistant Security

- Keep Home Assistant updated
- Use secure authentication
- Monitor integration logs for unusual activity

## Support

If you encounter issues not covered in this guide:

1. **Check Logs:** Enable debug logging and check for errors
2. **Search Issues:** Look through [GitHub Issues](https://github.com/cgfm/beszel-hass/issues)
3. **Create Issue:** Report bugs with logs and configuration details
4. **Ask Questions:** Use [GitHub Discussions](https://github.com/cgfm/beszel-hass/discussions)

For Beszel server issues, consult the [Beszel documentation](https://github.com/henrygd/beszel).
