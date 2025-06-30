# Beispiel Home Assistant Konfiguration

## Grundkonfiguration

```yaml
# configuration.yaml

# Standard Home Assistant Konfiguration
default_config:

# Beszel Integration (wird über UI konfiguriert)
# Die Integration erscheint automatisch nach Installation

# Optional: Erweiterte Logging-Konfiguration
logger:
  default: info
  logs:
    custom_components.beszel: debug

# Optional: Automationen basierend auf Beszel-Daten
automation:
  - alias: "Server CPU Warning"
    trigger:
      platform: numeric_state
      entity_id: sensor.my_server_cpu_usage
      above: 80
    action:
      service: notify.mobile_app_my_phone
      data:
        message: "Server CPU usage is high: {{ states('sensor.my_server_cpu_usage') }}%"

  - alias: "Server Offline Alert"
    trigger:
      platform: state
      entity_id: binary_sensor.my_server_status
      to: 'off'
      for:
        minutes: 5
    action:
      service: notify.mobile_app_my_phone
      data:
        message: "Server {{ trigger.to_state.attributes.system_name }} is offline!"

# Optional: Dashboard-Karten
lovelace:
  mode: yaml
  resources:
    - url: /local/mini-graph-card-bundle.js
      type: module
  dashboards:
    server-monitoring:
      mode: yaml
      filename: server-dashboard.yaml
      title: Server Monitoring
      icon: mdi:server
      show_in_sidebar: true
```

## Dashboard Beispiel

```yaml
# server-dashboard.yaml

title: Server Monitoring
views:
  - title: Übersicht
    cards:
      - type: entities
        title: Server Status
        entities:
          - binary_sensor.my_server_status
          - sensor.my_server_cpu_usage
          - sensor.my_server_memory_usage
          - sensor.my_server_disk_usage

      - type: custom:mini-graph-card
        title: CPU Usage
        entities:
          - sensor.my_server_cpu_usage
        hours_to_show: 24
        points_per_hour: 4
        line_color: red
        line_width: 2

      - type: custom:mini-graph-card
        title: Memory Usage
        entities:
          - sensor.my_server_memory_usage
        hours_to_show: 24
        points_per_hour: 4
        line_color: blue
        line_width: 2

      - type: gauge
        title: Disk Usage
        entity: sensor.my_server_disk_usage
        min: 0
        max: 100
        severity:
          green: 0
          yellow: 70
          red: 90

      - type: entities
        title: Network
        entities:
          - sensor.my_server_network_upload
          - sensor.my_server_network_download

      - type: entities
        title: System Info
        entities:
          - sensor.my_server_temperature
          - sensor.my_server_uptime
```

## Node-RED Integration

```json
[
    {
        "id": "server_monitoring_flow",
        "type": "tab",
        "label": "Server Monitoring"
    },
    {
        "id": "cpu_monitor",
        "type": "server-state-changed",
        "z": "server_monitoring_flow",
        "name": "CPU Usage Monitor",
        "server": "home_assistant_server",
        "version": 2,
        "exposeToHomeAssistant": false,
        "haConfig": [],
        "entityidfilter": "sensor.my_server_cpu_usage",
        "entityidfiltertype": "exact",
        "outputinitially": false,
        "state_type": "num",
        "haltifstate": "80",
        "halt_if_type": "num",
        "halt_if_compare": "gt",
        "outputs": 2,
        "output_only_on_state_change": true,
        "for": 0,
        "forType": "num",
        "forUnits": "minutes",
        "ignorePrevStateNull": false,
        "ignorePrevStateUnknown": false,
        "ignorePrevStateUnavailable": false,
        "ignoreCurrentStateUnknown": false,
        "ignoreCurrentStateUnavailable": false,
        "outputProperties": [],
        "x": 200,
        "y": 100,
        "wires": [
            ["notification_node"],
            []
        ]
    }
]
```

## Grafana Integration

```yaml
# Beispiel für Grafana Dashboard JSON
{
  "dashboard": {
    "title": "Beszel Server Monitoring",
    "panels": [
      {
        "title": "CPU Usage",
        "type": "stat",
        "targets": [
          {
            "expr": "homeassistant_sensor_percent{entity=\"sensor.my_server_cpu_usage\"}",
            "refId": "A"
          }
        ]
      }
    ]
  }
}
```

## Erweiterte Automationen

```yaml
# Komplexere Automationen für Server-Monitoring

automation:
  # Adaptive CPU-Überwachung basierend auf Tageszeit
  - alias: "Adaptive CPU Monitoring"
    trigger:
      platform: numeric_state
      entity_id: sensor.my_server_cpu_usage
      above: >
        {% if now().hour >= 9 and now().hour <= 17 %}
          90
        {% else %}
          70
        {% endif %}
    condition:
      condition: time
      weekday:
        - mon
        - tue
        - wed
        - thu
        - fri
    action:
      service: notify.critical_alerts
      data:
        message: >
          Server CPU usage is {{ states('sensor.my_server_cpu_usage') }}% 
          during {% if now().hour >= 9 and now().hour <= 17 %}business{% else %}off{% endif %} hours

  # Speicher-Trend-Überwachung
  - alias: "Memory Trend Alert"
    trigger:
      platform: template
      value_template: >
        {{ 
          (states('sensor.my_server_memory_usage') | float) - 
          (state_attr('sensor.my_server_memory_usage', 'previous_value') | float(0)) 
          > 10 
        }}
    action:
      service: notify.admins
      data:
        message: "Memory usage increased by more than 10% in the last update"

  # Kombinierte System-Health-Bewertung
  - alias: "System Health Score"
    trigger:
      platform: time_pattern
      minutes: "/15"
    action:
      service: input_number.set_value
      target:
        entity_id: input_number.server_health_score
      data:
        value: >
          {% set cpu = states('sensor.my_server_cpu_usage') | float(0) %}
          {% set mem = states('sensor.my_server_memory_usage') | float(0) %}
          {% set disk = states('sensor.my_server_disk_usage') | float(0) %}
          {% set temp = states('sensor.my_server_temperature') | float(0) %}
          
          {% set cpu_score = 100 - cpu if cpu <= 100 else 0 %}
          {% set mem_score = 100 - mem if mem <= 100 else 0 %}
          {% set disk_score = 100 - disk if disk <= 100 else 0 %}
          {% set temp_score = 100 - (temp - 20) * 2 if temp >= 20 and temp <= 70 else 0 %}
          
          {{ ((cpu_score + mem_score + disk_score + temp_score) / 4) | round(1) }}
```
