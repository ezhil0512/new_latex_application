"""AI model routing interface."""

from pathlib import Path
from typing import Protocol
import logging

from new_latex_app.domain.entities import DocumentRegion, PageImage, RecognizedContent

logger: logging.Logger = logging.getLogger(__name__)


class ModelRouter(Protocol):
    """Route regions to specialized offline model adapters."""

    def recognize(
        self,
        pages: tuple[PageImage, ...],
        regions: tuple[DocumentRegion, ...],
        workspace_path: Path,
    ) -> tuple[RecognizedContent, ...]:
        """Return recognized content without persisting OCR text."""
        ...
