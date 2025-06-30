# Docker Container Monitoring

The Beszel Home Assistant integration supports optional monitoring of Docker containers. This feature allows you to track the resource usage and status of individual Docker containers alongside your system metrics.

## Overview

When Docker monitoring is enabled, the integration will:
- Discover all Docker containers monitored by Beszel
- Create separate devices for each container in Home Assistant
- Provide detailed metrics for CPU, memory, and network usage
- Monitor container status (running/stopped)

## Requirements

### Beszel Server Configuration
Your Beszel instance must be configured to monitor Docker containers:

1. **Docker Socket Access**: Beszel needs access to the Docker socket
2. **Container Collection**: The `docker` collection must exist in PocketBase
3. **Agent Configuration**: Beszel agents must be configured to collect Docker stats

### Integration Configuration
Enable Docker monitoring during integration setup:
- ☑️ **Monitor Docker Containers** - Check this option during configuration

## Entities Created

For each Docker container, the following entities are created:

### Sensors
- **CPU Usage** (`sensor.docker_{container_name}_cpu_usage`)
  - Unit: `%`
  - Current CPU utilization of the container

- **Memory Usage** (`sensor.docker_{container_name}_memory_usage`)
  - Unit: `%`
  - Current memory utilization percentage of the container

- **Memory Usage (Bytes)** (`sensor.docker_{container_name}_memory_bytes`)
  - Unit: `bytes`
  - Absolute memory usage in bytes

- **Network RX** (`sensor.docker_{container_name}_network_rx`)
  - Unit: `bytes`
  - Total bytes received by the container

- **Network TX** (`sensor.docker_{container_name}_network_tx`)
  - Unit: `bytes`
  - Total bytes transmitted by the container

### Binary Sensors
- **Container Status** (`binary_sensor.docker_{container_name}_status`)
  - Device Class: `running`
  - Shows whether the container is currently running (`on`) or stopped (`off`)

## Device Information

Each Docker container appears as a separate device with the following information:
- **Name**: `Docker: {container_name}`
- **Manufacturer**: `Docker`
- **Model**: `Container`
- **Identifiers**: `docker_{container_id}`

## State Attributes

Each entity includes additional state attributes with detailed container information:

### Common Attributes
- `container_id` - Docker container ID
- `container_name` - Container name
- `image` - Docker image used
- `status` - Current container status
- `created` - Container creation timestamp
- `updated` - Last update timestamp

### Additional Sensor Attributes
Docker sensors also include all current stats as attributes:
- `cpu_percent` - CPU usage percentage
- `memory_percent` - Memory usage percentage
- `memory_usage` - Memory usage in bytes
- `memory_limit` - Memory limit in bytes
- `network_rx` - Network received bytes
- `network_tx` - Network transmitted bytes
- `block_io_read` - Block I/O read bytes
- `block_io_write` - Block I/O write bytes

### Binary Sensor Attributes
Docker binary sensors include additional container metadata:
- `ports` - Container port mappings
- `labels` - Container labels

## Data Source

Docker container data is retrieved from the Beszel PocketBase `docker` collection via the API endpoint:
```
GET /api/collections/docker/records
```

The integration fetches both container information and real-time statistics, combining them to provide comprehensive monitoring data.

## Configuration Examples

### Enable Docker Monitoring
When setting up the integration:
1. Fill in your Beszel server details
2. ☑️ Check "Monitor Docker Containers"
3. Complete the configuration

### Disable Docker Monitoring
If you want to disable Docker monitoring:
1. Go to **Settings** > **Devices & Services** > **Beszel**
2. Click **Configure** on your Beszel integration
3. ☐ Uncheck "Monitor Docker Containers"
4. Click **Submit**

Note: Disabling Docker monitoring will remove all Docker-related entities and devices.

## Dashboard Integration

### Suggested Cards

#### Container Overview
Use a **Glance Card** to show all container statuses:
```yaml
type: glance
title: Docker Containers
entities:
  - binary_sensor.docker_nginx_status
  - binary_sensor.docker_database_status
  - binary_sensor.docker_redis_status
```

#### Container Resources
Use **Gauge Cards** for resource monitoring:
```yaml
type: gauge
title: Container CPU Usage
entity: sensor.docker_nginx_cpu_usage
min: 0
max: 100
severity:
  green: 0
  yellow: 70
  red: 90
```

#### Resource History
Use **History Graph** for trends:
```yaml
type: history-graph
title: Container Resource Usage
entities:
  - sensor.docker_nginx_cpu_usage
  - sensor.docker_nginx_memory_usage
hours_to_show: 24
```

## Troubleshooting

### No Docker Containers Found
- **Verify Beszel Configuration**: Check that Beszel is configured to monitor Docker
- **Check Container Collection**: Ensure the `docker` collection exists in PocketBase
- **Agent Configuration**: Verify Beszel agents are collecting Docker stats
- **User Permissions**: Ensure your Beszel user has access to the docker collection

### Container Data Missing
- **Container Status**: Ensure containers are running and being monitored
- **API Access**: Verify the docker collection API is accessible
- **Collection Schema**: Check that the docker collection has the expected fields

### Performance Considerations
- **Large Number of Containers**: With many containers, consider the polling interval
- **Resource Usage**: Docker monitoring adds to the data fetched from Beszel
- **Network Traffic**: Each container adds to the API calls made to Beszel

### Debug Information
Enable debug logging to troubleshoot Docker monitoring:
```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.beszel: debug
```

Look for log entries related to:
- Docker container discovery
- Docker data fetching
- Container entity creation

## API Reference

The integration uses the following Beszel API endpoints for Docker monitoring:

### Get Docker Containers
```http
GET /api/collections/docker/records
Authorization: Bearer {token}
```

Response includes container information and current statistics.

### Data Structure
Expected data structure from Beszel:
```json
{
  "items": [
    {
      "id": "container_id",
      "name": "container_name",
      "image": "image:tag",
      "status": "running",
      "created": "2024-01-01T00:00:00Z",
      "updated": "2024-01-01T00:00:00Z",
      "stats": {
        "cpu_percent": 15.5,
        "memory_percent": 45.2,
        "memory_usage": 134217728,
        "memory_limit": 268435456,
        "network_rx": 1048576,
        "network_tx": 2097152,
        "block_io_read": 4194304,
        "block_io_write": 8388608
      }
    }
  ]
}
```

## Best Practices

1. **Selective Monitoring**: Only enable Docker monitoring if you need container-level metrics
2. **Resource Management**: Monitor Home Assistant resource usage with many containers
3. **Naming Conventions**: Use clear container names for easy identification in Home Assistant
4. **Dashboard Organization**: Group container entities by service or application
5. **Alerting**: Set up automations for container status changes or resource thresholds

## Migration Notes

### From System-Only Monitoring
If you're upgrading from system-only monitoring:
1. Docker monitoring is disabled by default
2. Enabling it requires reconfiguration of the integration
3. New entities will be created for Docker containers
4. Existing system entities remain unchanged

### Disabling Docker Monitoring
If you disable Docker monitoring:
1. All Docker-related entities will be removed
2. Docker devices will be deleted
3. System monitoring continues unchanged
4. Historical data for Docker entities will be preserved but entities will be unavailable
