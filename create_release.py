#!/usr/bin/env python3
"""Build a Beszel integration release archive."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent
INTEGRATION = ROOT / "custom_components" / "beszel"


def create_release_package(output_directory: Path = ROOT) -> Path:
    """Create and return the release ZIP path."""
    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    staging = output_directory / f"release-{version}"
    archive = output_directory / f"beszel-hass-{version}.zip"

    if staging.exists():
        shutil.rmtree(staging)
    if archive.exists():
        archive.unlink()
    destination = staging / "custom_components" / "beszel"
    shutil.copytree(
        INTEGRATION,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )
    for filename in ("README.md", "INSTALLATION.md", "CHANGELOG.md", "LICENSE"):
        shutil.copy2(ROOT / filename, staging / filename)
    shutil.copy2(ROOT / "hacs.json", staging / "hacs.json")

    (staging / "INSTALLATION.txt").write_text(
        """Beszel Home Assistant Integration

HACS:
Add https://github.com/cgfm/beszel-hass as a custom Integration repository,
install Beszel, and restart Home Assistant.

Manual:
Copy custom_components/beszel to the Home Assistant configuration directory,
restart Home Assistant, then add Beszel under Settings > Devices & services.

See INSTALLATION.md for configuration and security guidance.
""",
        encoding="utf-8",
    )

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                zip_file.write(path, path.relative_to(staging))

    print(f"Created {archive.name} for version {version}")
    return archive


if __name__ == "__main__":
    create_release_package()
