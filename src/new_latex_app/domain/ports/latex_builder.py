"""LaTeX builder interface."""

from pathlib import Path
from typing import Protocol
import logging

from new_latex_app.domain.entities import DocumentStructure, LatexDocument

logger: logging.Logger = logging.getLogger(__name__)


class LatexBuilder(Protocol):
    """Render a document structure into compile-ready LaTeX."""

    def build(self, structure: DocumentStructure, workspace_path: Path) -> LatexDocument:
        """Return a temporary LaTeX artifact."""
        ...
