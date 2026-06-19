"""Rotating logging configuration with sensitive-content safeguards."""

from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any
import logging
import sys

import yaml

from new_latex_app.domain.exceptions import ConfigurationError

logger: logging.Logger = logging.getLogger(__name__)


class LoggingConfigurator:
    """Configure console and rotating file logging."""

    def __init__(self, config_dir: Path) -> None:
        """Create a logging configurator."""
        self._config_dir = config_dir

    def configure(self) -> None:
        """Configure root logging from `logging.yaml`."""
        config = self._read_config()
        section = config.get("logging", {})
        if not isinstance(section, dict):
            raise ConfigurationError("logging section must be a mapping")
        level = str(section.get("level", "INFO")).upper()
        log_dir = Path(str(section.get("directory", "logs")))
        log_dir.mkdir(parents=True, exist_ok=True)
        formatter = logging.Formatter(str(section.get("format", "%(asctime)s | %(levelname)s | %(name)s | %(message)s")))

        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.handlers.clear()

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        file_handler = RotatingFileHandler(
            log_dir / str(section.get("filename", "new_latex_app.log")),
            maxBytes=int(section.get("max_bytes", 10_485_760)),
            backupCount=int(section.get("backup_count", 5)),
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        logger.info("Logging configured")

    def _read_config(self) -> dict[str, Any]:
        """Read logging YAML configuration."""
        path = self._config_dir / "logging.yaml"
        if not path.exists():
            raise ConfigurationError(f"Logging configuration file not found: {path}")
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
        if not isinstance(data, dict):
            raise ConfigurationError("Logging configuration must contain a mapping")
        return data
