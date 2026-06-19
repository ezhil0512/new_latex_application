"""Math OCR recognition interface."""

from pathlib import Path
from typing import Protocol
import logging

from new_latex_app.domain.entities import DocumentRegion, PageImage, RecognizedContent

logger: logging.Logger = logging.getLogger(__name__)


class MathOcrRecognizer(Protocol):
    """Recognize mathematical expressions from formula regions only."""

    def recognize_math(
        self,
        pages: tuple[PageImage, ...],
        regions: tuple[DocumentRegion, ...],
        workspace_path: Path,
    ) -> tuple[RecognizedContent, ...]:
        """Return recognized mathematical content for formula regions."""
        ...
