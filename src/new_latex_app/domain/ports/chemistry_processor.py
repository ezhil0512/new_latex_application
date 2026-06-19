"""Chemistry processor interface for chemistry-specific text normalization."""

from typing import Protocol
import logging

from new_latex_app.domain.entities import DocumentStructure

logger: logging.Logger = logging.getLogger(__name__)


class ChemistryProcessor(Protocol):
    """Normalize chemistry-specific content inside a document structure."""

    def process(self, structure: DocumentStructure) -> DocumentStructure:
        """Return a document structure with chemistry metadata and normalization."""
        ...
