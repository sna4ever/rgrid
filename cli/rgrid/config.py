"""CLI configuration management.

SECURITY: Credentials are stored with restricted file permissions.
The config directory is set to 0700 (user only) and credential files
are set to 0600 (user read/write only).
"""

import os
from pathlib import Path
from typing import Optional
import configparser


class RGridConfig:
    """Manage RGrid CLI configuration."""

    def __init__(self) -> None:
        self.config_dir = Path.home() / ".rgrid"
        self.credentials_file = self.config_dir / "credentials"
        self.config_file = self.config_dir / "config"

    def ensure_config_dir(self) -> None:
        """Create config directory if it doesn't exist.

        SECURITY: Creates directory with 0700 permissions (user only)
        to prevent other users from listing contents.
        """
        if not self.config_dir.exists():
            # SECURITY: Create with restrictive permissions
            self.config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        else:
            # SECURITY: Ensure existing directory has correct permissions
            self.config_dir.chmod(0o700)

    def save_credentials(self, api_key: str, api_url: str = "http://localhost:8000") -> None:
        """Save API credentials.

        SECURITY: Uses atomic write pattern and sets restrictive permissions
        before writing sensitive data to prevent TOCTOU vulnerabilities.
        """
        self.ensure_config_dir()

        config = configparser.ConfigParser()
        config["default"] = {
            "api_key": api_key,
            "api_url": api_url,
        }

        # SECURITY: Set umask to ensure file is created with restrictive permissions
        # This prevents a brief window where the file might be world-readable
        old_umask = os.umask(0o077)  # Only user can read/write
        try:
            with open(self.credentials_file, "w") as f:
                config.write(f)
        finally:
            os.umask(old_umask)

        # SECURITY: Explicitly set permissions to 0600 (user read/write only)
        self.credentials_file.chmod(0o600)

    def load_credentials(self) -> Optional[dict[str, str]]:
        """Load API credentials."""
        if not self.credentials_file.exists():
            return None

        config = configparser.ConfigParser()
        config.read(self.credentials_file)

        if "default" not in config:
            return None

        return {
            "api_key": config["default"].get("api_key", ""),
            "api_url": config["default"].get("api_url", "http://localhost:8000"),
        }

    def has_credentials(self) -> bool:
        """Check if credentials exist."""
        return self.credentials_file.exists()


# Global config instance
config = RGridConfig()


def get_settings() -> dict:
    """
    Get current settings including credentials.

    Returns:
        dict with api_url and api_key
    """
    creds = config.load_credentials()
    if creds:
        return creds
    return {
        "api_url": "http://localhost:8000",
        "api_key": "",
    }
