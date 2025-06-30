# Contributing to Beszel Home Assistant Integration

Thank you for your interest in contributing to this integration!

## Development Environment Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/cgfm/beszel-hass
   cd beszel-hass
   ```

2. Create a virtual Python environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -r requirements_dev.txt
   ```

4. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Code Style and Quality

This project uses several tools to maintain code quality:

- **[Black](https://black.readthedocs.io/)** for code formatting
- **[isort](https://pycqa.github.io/isort/)** for import sorting  
- **[Pylint](https://pylint.org/)** for code analysis
- **[mypy](https://mypy.readthedocs.io/)** for type checking

Run these tools before committing:

```bash
black custom_components/beszel/
isort custom_components/beszel/
pylint custom_components/beszel/
mypy custom_components/beszel/
```

Or simply run pre-commit to check everything:

```bash
pre-commit run --all-files
```

## Testing

### Manual Testing

1. Test the integration with a real Beszel instance:
   ```bash
   python test_simple.py localhost 8090 admin password
   ```

2. Test in Home Assistant:
   - Copy `custom_components/beszel` to your HA `config/custom_components/`
   - Restart Home Assistant
   - Add the integration through the UI

### Automated Testing

Write tests for new features in the `tests/` directory:

```bash
pytest tests/
```

## Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Make** your changes
4. **Run** code quality checks: `pre-commit run --all-files`
5. **Test** your changes manually and with automated tests
6. **Commit** your changes: `git commit -m 'Add amazing feature'`
7. **Push** to your branch: `git push origin feature/amazing-feature`
8. **Open** a Pull Request

### Pull Request Guidelines

- **Clear description**: Explain what your PR does and why
- **Small changes**: Keep PRs focused on a single feature or fix
- **Test coverage**: Include tests for new functionality
- **Documentation**: Update README or docs if needed
- **No breaking changes**: Maintain backward compatibility when possible

## Development Guidelines

### Code Organization

- **`api.py`**: PocketBase API client
- **`config_flow.py`**: Configuration flow for setup
- **`coordinator.py`**: Data update coordinator
- **`sensor.py`**: Sensor entities
- **`binary_sensor.py`**: Binary sensor entities
- **`const.py`**: Constants and configuration
- **`device.py`**: Device registry management

### Adding New Sensor Types

1. Add sensor definition to `const.py`:
   ```python
   SENSOR_TYPES = {
       "new_metric": {
           "name": "New Metric",
           "unit": "unit",
           "icon": "mdi:icon",
           "device_class": SensorDeviceClass.MEASUREMENT,
           "state_class": SensorStateClass.MEASUREMENT,
       },
   }
   ```

2. Update `sensor.py` to handle the new metric
3. Add translation strings to `strings.py` and translation files
4. Test with real Beszel data

### API Changes

When modifying the API client:

1. Ensure backward compatibility
2. Add proper error handling
3. Update docstrings
4. Test with real Beszel instance

## Reporting Issues

### Bug Reports

Include:
- Home Assistant version
- Integration version
- Beszel version
- Error logs (with debug logging enabled)
- Steps to reproduce

### Feature Requests

Include:
- Use case description
- Proposed implementation
- Example data/screenshots if applicable

## Questions and Discussions

- Use [GitHub Discussions](https://github.com/cgfm/beszel-hass/discussions) for questions
- Use [GitHub Issues](https://github.com/cgfm/beszel-hass/issues) for bugs and feature requests

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
4. Erstellen Sie einen Pull Request

## Melden von Problemen

Bitte verwenden Sie das GitHub Issues System, um Bugs oder Feature-Requests zu melden.

## Code of Conduct

Wir erwarten von allen Mitwirkenden respektvolles und professionelles Verhalten.
