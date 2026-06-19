"""Rule engine interface."""

from typing import Protocol
import logging

from new_latex_app.domain.entities import DocumentStructure

logger: logging.Logger = logging.getLogger(__name__)


class RuleEngine(Protocol):
    """Apply deterministic cleanup and document-structure rules."""

    def apply(self, structure: DocumentStructure) -> DocumentStructure:
        """Return a normalized document structure."""
        ...
