"""Concrete pass-through PDF compiler adapter."""

from pathlib import Path
import logging
import time

from new_latex_app.domain.entities import CompiledPdf, LatexDocument

logger: logging.Logger = logging.getLogger(__name__)


class PassThroughPdfCompiler:
    """Pass-through PDF compiler for offline LaTeX generation.

    This adapter satisfies the ``PdfCompiler`` contract by returning a
    ``CompiledPdf`` that points to the LaTeX output path rather than a
    real PDF.  No TeX distribution is invoked.  This unblocks the pipeline
    so that generated LaTeX can reach the frontend while a full compiler
    adapter is not yet available.
    """

    def compile(self, latex_document: LatexDocument, workspace_path: Path) -> CompiledPdf:
        """Return a placeholder CompiledPdf without invoking a TeX engine."""
        started_at = time.perf_counter()
        logger.info("PDF compilation skipped (pass-through mode)")

        # Use the LaTeX output path as the PDF path sentinel.
        # When a real TeX engine is wired in this will be replaced by the
        # actual compiled PDF path.
        pdf_path = latex_document.output_path if latex_document.output_path is not None else (
            workspace_path / "output.pdf"
        )

        logger.info(
            "PDF compilation pass-through completed in %.3fs",
            time.perf_counter() - started_at,
        )
        return CompiledPdf(path=pdf_path, engine="none")
