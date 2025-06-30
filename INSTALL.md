# Installation und Entwicklung

## Für Endbenutzer

### Installation über HACS

1. Öffnen Sie HACS in Home Assistant
2. Gehen Sie zu "Integrations"
3. Klicken Sie auf die drei Punkte oben rechts → "Custom repositories"
4. Fügen Sie die Repository-URL hinzu: `https://github.com/YOURUSERNAME/beszel-hass`
5. Wählen Sie "Integration" als Kategorie
6. Klicken Sie auf "Add"
7. Suchen Sie nach "Beszel" und installieren Sie es
8. Starten Sie Home Assistant neu

### Manuelle Installation

1. Laden Sie die neueste Version von der [Releases-Seite](https://github.com/YOURUSERNAME/beszel-hass/releases) herunter
2. Extrahieren Sie die ZIP-Datei
3. Kopieren Sie den `custom_components/beszel` Ordner in Ihr `config/custom_components/` Verzeichnis
4. Starten Sie Home Assistant neu

## Für Entwickler

### Entwicklungsumgebung einrichten

1. Klonen Sie das Repository:
   ```bash
   git clone https://github.com/YOURUSERNAME/beszel-hass.git
   cd beszel-hass
   ```

2. Erstellen Sie eine virtuelle Umgebung:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # oder
   venv\Scripts\activate     # Windows
   ```

3. Führen Sie das Setup-Skript aus:
   ```bash
   python setup_dev.py
   ```

### Home Assistant Entwicklungsumgebung

1. Installieren Sie Home Assistant Core in einer Entwicklungsumgebung:
   ```bash
   pip install homeassistant
   ```

2. Erstellen Sie eine Testkonfiguration:
   ```bash
   mkdir ha_test_config
   cd ha_test_config
   ```

3. Erstellen Sie eine `configuration.yaml`:
   ```yaml
   default_config:
   logger:
     default: info
     logs:
       custom_components.beszel: debug
   ```

4. Verlinken Sie Ihre Integration:
   ```bash
   mkdir -p custom_components
   ln -s /path/to/beszel-hass/custom_components/beszel custom_components/beszel
   ```

5. Starten Sie Home Assistant:
   ```bash
   hass -c .
   ```

### Code-Qualität

Vor dem Commit sollten Sie immer folgende Befehle ausführen:

```bash
# Code formatieren
black custom_components/beszel/

# Imports sortieren
isort custom_components/beszel/

# Linting
pylint custom_components/beszel/

# Type checking
mypy custom_components/beszel/

# Tests ausführen
pytest tests/
```

### Debugging

Aktivieren Sie Debug-Logging in Ihrer `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.beszel: debug
    custom_components.beszel.api: debug
    custom_components.beszel.coordinator: debug
```

### API-Endpunkte testen

Sie können die Beszel API direkt testen:

```bash
# Login
curl -X POST "http://your-beszel-host:8090/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "your-username", "password": "your-password"}'

# Systeme abrufen
curl -X GET "http://your-beszel-host:8090/api/systems" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Statistiken abrufen
curl -X GET "http://your-beszel-host:8090/api/systems/SYSTEM_ID/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Deployment

### Neue Version veröffentlichen

1. Aktualisieren Sie die Version in `manifest.json`
2. Erstellen Sie einen Git-Tag:
   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```
3. Die GitHub Action erstellt automatisch ein Release

### HACS-Validierung

Die Integration wird automatisch mit HACS validiert. Stellen Sie sicher, dass:

- `hacs.json` korrekt konfiguriert ist
- `manifest.json` alle erforderlichen Felder enthält
- Die Ordnerstruktur korrekt ist
- Alle Abhängigkeiten in `manifest.json` aufgelistet sind
