"""Input staging interface."""

from pathlib import Path
from typing import Protocol
import logging

logger: logging.Logger = logging.getLogger(__name__)


class InputStager(Protocol):
    """Stage user input into temporary workspace storage."""

    def stage(self, source_path: Path, workspace_path: Path) -> Path:
        """Return a temporary copy of the uploaded document."""
        ...
