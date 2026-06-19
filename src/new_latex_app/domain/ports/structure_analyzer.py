"""Document structure analyzer interface."""

from typing import Protocol
import logging

from new_latex_app.domain.entities import DocumentStructure, PageImage, RecognizedContent

logger: logging.Logger = logging.getLogger(__name__)


class DocumentStructureAnalyzer(Protocol):
    """Build a hierarchical document representation."""

    def analyze(
        self,
        pages: tuple[PageImage, ...],
        contents: tuple[RecognizedContent, ...],
    ) -> DocumentStructure:
        """Return structured document content."""
        ...
