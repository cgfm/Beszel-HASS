# Installation Guide

## Prerequisites

- Home Assistant 2024.12.0 or newer
- A reachable Beszel Hub and at least one configured system
- A Beszel account that can read the systems and supports password login

Test basic reachability from the Home Assistant network:

```bash
curl http://YOUR_BESZEL_HOST:8090/api/health
```

Use HTTPS instead when your Hub is behind a TLS reverse proxy. Do not put a scheme,
port, or path into the integration's **Host** field.

## HACS installation

1. Open **HACS → Integrations**.
2. Open the menu and choose **Custom repositories**.
3. Add `https://github.com/cgfm/beszel-hass` with category **Integration**.
4. Search for and install **Beszel**.
5. Restart Home Assistant.

## Manual installation

1. Download and extract the latest release archive.
2. Copy its `custom_components/beszel` directory to
   `<home-assistant-config>/custom_components/beszel`.
3. Restart Home Assistant.

The resulting layout must contain at least:

```text
config/
└── custom_components/
    └── beszel/
        ├── __init__.py
        ├── manifest.json
        ├── config_flow.py
        └── ...
```

## Add the integration

1. Open **Settings → Devices & services**.
2. Select **Add integration** and search for **Beszel**.
3. Enter the hostname or IP, port, HTTPS setting, email or username, and password.
4. Choose whether to monitor containers and set an update interval between 10 and
   3600 seconds.
5. Submit the form. The connection and system access are validated before the entry
   is saved.

After setup, systems appear as devices. Current containers and SMART disks receive
their own child devices. Newly discovered inventory is added without reloading the
integration.

## Change options

Open the Beszel integration and select **Configure**. Endpoint, credentials,
container discovery, and polling interval can all be changed. Home Assistant
validates the new settings and reloads the entry.

## Security

The password is stored in Home Assistant's config-entry storage; anyone with access
to that storage or its backups may be able to read it. The bearer token remains in
memory. HTTP also leaves both credentials unencrypted on the network. Protect Home
Assistant's files and backups, and prefer HTTPS or a trusted VPN outside a private,
controlled network. A dedicated read-only Beszel user is recommended where the
Hub's permission model permits it.

## Troubleshooting

### Cannot connect

- Verify the host, port, and HTTPS option.
- Test the `/api/health` URL from the Home Assistant network.
- Check firewalls, DNS, reverse-proxy certificates, and container networking.

### Invalid authentication

- Sign into the Beszel UI with the same username and password.
- Confirm password authentication is enabled; OAuth-only login is not supported.
- Use Home Assistant's reauthentication prompt after changing the password.

### Missing systems or containers

- Confirm the user can see them in the Beszel UI.
- Confirm agents are reporting current data.
- Confirm **Monitor containers** is enabled in the integration options.
- Wait for the configured polling interval; additions are discovered dynamically.

### Debug logging

```yaml
logger:
  logs:
    custom_components.beszel: debug
```

Restart Home Assistant, reproduce the issue, and inspect **Settings → System →
Logs**. Remove debug logging afterward because API diagnostics can be verbose.
