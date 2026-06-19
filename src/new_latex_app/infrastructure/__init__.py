"""Infrastructure adapters for configuration, logging, storage, and integrations."""

import logging

logger: logging.Logger = logging.getLogger(__name__)

__all__ = ["logger"]
