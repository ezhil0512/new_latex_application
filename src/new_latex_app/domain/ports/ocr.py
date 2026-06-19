"""OCR recognition interface."""

from pathlib import Path
from typing import Protocol
import logging

from new_latex_app.domain.entities import DocumentRegion, PageImage, RecognizedContent

logger: logging.Logger = logging.getLogger(__name__)


class TextOcrRecognizer(Protocol):
    """Recognize text from visual text regions only."""

    def recognize_text(
        self,
        pages: tuple[PageImage, ...],
        regions: tuple[DocumentRegion, ...],
        workspace_path: Path,
    ) -> tuple[RecognizedContent, ...]:
        """Return recognized text content for text regions."""
        ...
