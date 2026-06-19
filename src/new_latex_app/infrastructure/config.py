"""Configuration loading from YAML files and environment variables."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import logging
import os

from dotenv import load_dotenv
import yaml

from new_latex_app.domain.exceptions import ConfigurationError

logger: logging.Logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Validated application settings."""

    name: str
    environment: str
    config_dir: Path
    temp_root: Path | None
    max_pages: int
    max_upload_mb: int
    retain_outputs_after_response: bool
    log_sensitive_content: bool
    allow_network: bool
    compiler_engine: str
    compiler_timeout_seconds: int
    compiler_runs: int


class SettingsLoader:
    """Load application settings without hardcoded runtime values."""

    def __init__(self, config_dir: Path | None = None) -> None:
        """Create a settings loader."""
        load_dotenv()
        env_config_dir = os.getenv("NEW_LATEX_APP_CONFIG_DIR")
        self._config_dir = config_dir or Path(env_config_dir or "configs")
        logger.debug("Settings loader initialized")

    def load(self) -> AppSettings:
        """Load and validate settings from YAML and `.env` values."""
        data = self._read_yaml("app.yaml")
        app = self._as_mapping(data.get("app"), "app")
        security = self._as_mapping(data.get("security"), "security")
        compiler = self._as_mapping(data.get("compiler"), "compiler")
        try:
            settings = AppSettings(
                name=str(os.getenv("NEW_LATEX_APP_NAME", app["name"])),
                environment=str(os.getenv("NEW_LATEX_APP_ENV", app["environment"])),
                config_dir=self._config_dir,
                temp_root=self._optional_path(os.getenv("NEW_LATEX_APP_TEMP_ROOT", app.get("temp_root"))),
                max_pages=int(os.getenv("NEW_LATEX_APP_MAX_PAGES", app["max_pages"])),
                max_upload_mb=int(os.getenv("NEW_LATEX_APP_MAX_UPLOAD_MB", app["max_upload_mb"])),
                retain_outputs_after_response=self._to_bool(
                    os.getenv(
                        "NEW_LATEX_APP_RETAIN_OUTPUTS",
                        app["retain_outputs_after_response"],
                    )
                ),
                log_sensitive_content=self._to_bool(
                    os.getenv("NEW_LATEX_APP_LOG_SENSITIVE_CONTENT", security["log_sensitive_content"])
                ),
                allow_network=self._to_bool(os.getenv("NEW_LATEX_APP_ALLOW_NETWORK", security["allow_network"])),
                compiler_engine=str(os.getenv("NEW_LATEX_APP_COMPILER_ENGINE", compiler["engine"])),
                compiler_timeout_seconds=int(
                    os.getenv("NEW_LATEX_APP_COMPILER_TIMEOUT_SECONDS", compiler["timeout_seconds"])
                ),
                compiler_runs=int(os.getenv("NEW_LATEX_APP_COMPILER_RUNS", compiler["runs"])),
            )
            if settings.log_sensitive_content:
                raise ConfigurationError("Sensitive-content logging must remain disabled")
            if settings.allow_network:
                raise ConfigurationError("Network access must remain disabled")
            logger.info("Settings loaded")
            return settings
        except KeyError as error:
            logger.exception("Settings validation failed")
            raise ConfigurationError(f"Missing configuration key: {error}") from error

    def _read_yaml(self, filename: str) -> dict[str, Any]:
        """Read a YAML file from the configured directory."""
        path = self._config_dir / filename
        if not path.exists():
            raise ConfigurationError(f"Configuration file not found: {path}")
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
        if not isinstance(data, dict):
            raise ConfigurationError(f"Configuration file must contain a mapping: {path}")
        return data

    def _as_mapping(self, value: object, name: str) -> dict[str, Any]:
        """Validate a YAML section as a mapping."""
        if not isinstance(value, dict):
            raise ConfigurationError(f"Configuration section must be a mapping: {name}")
        return value

    def _optional_path(self, value: object) -> Path | None:
        """Convert an optional path-like value."""
        if value in (None, "", "null"):
            return None
        return Path(str(value))

    def _to_bool(self, value: object) -> bool:
        """Convert YAML or environment values to booleans."""
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
