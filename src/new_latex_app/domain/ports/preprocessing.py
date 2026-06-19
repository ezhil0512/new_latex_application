"""Image preprocessing interface."""

from pathlib import Path
from typing import Protocol
import logging

from new_latex_app.domain.entities import PageImage

logger: logging.Logger = logging.getLogger(__name__)


class ImagePreprocessor(Protocol):
    """Prepare page images for downstream analysis."""

    def preprocess(self, pages: tuple[PageImage, ...], workspace_path: Path) -> tuple[PageImage, ...]:
        """Return preprocessed page images stored in temporary workspace."""
        ...
