"""LaTeX validation interface."""

from typing import Protocol
import logging

from new_latex_app.domain.entities import LatexDocument

logger: logging.Logger = logging.getLogger(__name__)


class ValidationEngine(Protocol):
    """Validate generated LaTeX before compilation."""

    def validate(self, latex_document: LatexDocument) -> LatexDocument:
        """Return the validated LaTeX document or raise a validation error."""
        ...
