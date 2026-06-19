"""Unit tests for configuration loading."""

from pathlib import Path
import logging

from new_latex_app.infrastructure.config import SettingsLoader

logger: logging.Logger = logging.getLogger(__name__)


def test_settings_loader_reads_default_config() -> None:
    """Settings loader should read the checked-in config files."""
    settings = SettingsLoader(config_dir=Path("configs")).load()
    logger.info("Settings loader test completed")
    assert settings.name == "new_latex_app"
    assert settings.allow_network is False
    assert settings.log_sensitive_content is False
