"""CLI configuration management."""

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
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def save_credentials(self, api_key: str, api_url: str = "http://localhost:8000") -> None:
        """Save API credentials."""
        self.ensure_config_dir()

        config = configparser.ConfigParser()
        config["default"] = {
            "api_key": api_key,
            "api_url": api_url,
        }

        with open(self.credentials_file, "w") as f:
            config.write(f)

        # Set permissions to 0600 (user read/write only)
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
