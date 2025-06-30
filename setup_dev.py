#!/usr/bin/env python3
"""Setup script for development environment."""

import subprocess
import sys
from pathlib import Path


def run_command(command: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"Running: {command}")
    return subprocess.run(command, shell=True, check=check)


def main():
    """Set up the development environment."""
    print("Setting up Beszel Home Assistant Integration development environment...")
    
    # Install development requirements
    print("\n1. Installing development requirements...")
    run_command(f"{sys.executable} -m pip install -r requirements_dev.txt")
    
    # Install pre-commit hooks (optional)
    print("\n2. Setting up pre-commit hooks...")
    try:
        run_command("pre-commit install", check=False)
    except FileNotFoundError:
        print("pre-commit not found, skipping pre-commit hooks setup")
    
    # Run initial checks
    print("\n3. Running initial code quality checks...")
    
    # Format code
    print("\nFormatting code with black...")
    run_command("black custom_components/beszel/", check=False)
    
    # Sort imports
    print("\nSorting imports with isort...")
    run_command("isort custom_components/beszel/", check=False)
    
    # Run linting
    print("\nRunning pylint...")
    run_command("pylint custom_components/beszel/", check=False)
    
    # Run type checking
    print("\nRunning mypy...")
    run_command("mypy custom_components/beszel/", check=False)
    
    print("\n✅ Development environment setup complete!")
    print("\nNext steps:")
    print("1. Update the manifest.json with your GitHub username")
    print("2. Update the README.md with your repository URLs")
    print("3. Create a GitHub repository and push the code")
    print("4. Test the integration in a Home Assistant development environment")


if __name__ == "__main__":
    main()
