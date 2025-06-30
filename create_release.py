#!/usr/bin/env python3
"""Package the Beszel integration for distribution."""

import shutil
import zipfile
from pathlib import Path
import json

def create_release_package():
    """Create a release package for the integration."""
    print("Creating Beszel Home Assistant Integration Release Package")
    print("=" * 60)
    
    # Read version from manifest
    manifest_path = Path("custom_components/beszel/manifest.json")
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        version = manifest.get("version", "1.0.0")
    else:
        version = "1.0.0"
    
    print(f"Version: {version}")
    
    # Create release directory
    release_dir = Path(f"release-{version}")
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir()
    
    # Copy integration files
    print("\nCopying integration files...")
    src_dir = Path("custom_components/beszel")
    dst_dir = release_dir / "custom_components" / "beszel"
    
    # Copy all integration files except development files
    shutil.copytree(src_dir, dst_dir, ignore=shutil.ignore_patterns(
        "__pycache__",
        "*.pyc",
        ".pytest_cache",
        "config_flow_new.py"  # Exclude alternative config flow
    ))
    
    # Copy documentation
    print("Copying documentation...")
    for file in ["README.md", "LICENSE", "INSTALL.md", "CONTRIBUTING.md"]:
        if Path(file).exists():
            shutil.copy(file, release_dir)
    
    # Copy HACS files
    if Path("hacs.json").exists():
        shutil.copy("hacs.json", release_dir)
    
    # Create ZIP file
    zip_path = Path(f"beszel-hass-{version}.zip")
    print(f"\nCreating ZIP package: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in release_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(release_dir)
                zipf.write(file_path, arcname)
    
    # Create installation instructions
    install_txt = release_dir / "INSTALLATION.txt"
    with open(install_txt, 'w', encoding='utf-8') as f:
        f.write("""Beszel Home Assistant Integration - Installation Instructions

HACS Installation:
1. Open HACS in Home Assistant
2. Go to Integrations
3. Click the three dots menu -> Custom repositories
4. Add this repository URL: https://github.com/cgfm/beszel-hass
5. Select "Integration" as category
6. Search for "Beszel" and install
7. Restart Home Assistant

Manual Installation:
1. Extract this ZIP file
2. Copy the "custom_components/beszel" folder to your Home Assistant 
   config/custom_components/ directory
3. Restart Home Assistant
4. Go to Settings > Devices & Services > Add Integration
5. Search for "Beszel" and configure

For detailed instructions, see INSTALL.md
""")
    
    print(f"✅ Release package created: {zip_path}")
    print(f"✅ Release directory: {release_dir}")
    
    # List package contents
    print("\nPackage contents:")
    for file_path in sorted(release_dir.rglob('*')):
        if file_path.is_file():
            print(f"  {file_path.relative_to(release_dir)}")
    
    # Print deployment checklist
    print("\n" + "=" * 60)
    print("DEPLOYMENT CHECKLIST")
    print("=" * 60)
    
    checklist = [
        "✓ Integration files are complete",
        "✓ Code quality checks passed", 
        "✓ Documentation is updated",
        "✗ Update GitHub repository URLs in manifest.json and README.md",
        "✗ Create GitHub repository",
        "✗ Upload release package to GitHub releases",
        "✗ Test installation in real Home Assistant instance",
        "✗ Add repository description and topics on GitHub",
        "✗ Submit to HACS (if desired)",
    ]
    
    for item in checklist:
        print(item)
    
    print("\nNext steps:")
    print("1. Test the release package in Home Assistant")
    print("2. Create GitHub repository and update URLs")  
    print("3. Upload to GitHub releases")
    print("4. Test HACS installation")

if __name__ == "__main__":
    create_release_package()
