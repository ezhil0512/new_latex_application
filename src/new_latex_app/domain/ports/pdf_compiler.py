"""PDF compiler interface."""

from pathlib import Path
from typing import Protocol
import logging

from new_latex_app.domain.entities import CompiledPdf, LatexDocument

logger: logging.Logger = logging.getLogger(__name__)


class PdfCompiler(Protocol):
    """Compile LaTeX into a PDF using a local TeX distribution."""

    def compile(self, latex_document: LatexDocument, workspace_path: Path) -> CompiledPdf:
        """Compile LaTeX and return a temporary PDF artifact."""
        ...
