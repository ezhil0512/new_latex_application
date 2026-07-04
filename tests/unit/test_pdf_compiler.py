"""Unit tests for the pass-through PDF compiler adapter."""

from pathlib import Path
import logging

from new_latex_app.domain.entities import CompiledPdf, LatexDocument
from new_latex_app.infrastructure.adapters.pdf_compiler import PassThroughPdfCompiler

logger: logging.Logger = logging.getLogger(__name__)


def test_pdf_compiler_returns_compiled_pdf(tmp_path: Path) -> None:
    """The pass-through compiler should return a CompiledPdf instance."""
    compiler = PassThroughPdfCompiler()
    doc = LatexDocument(
        source="\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}",
        output_path=tmp_path / "exam.tex",
    )

    result = compiler.compile(doc, tmp_path)

    assert isinstance(result, CompiledPdf)
    logger.info("PDF compiler return type test completed")


def test_pdf_compiler_uses_latex_output_path(tmp_path: Path) -> None:
    """The returned PDF path should match the LaTeX document output_path."""
    compiler = PassThroughPdfCompiler()
    tex_path = tmp_path / "exam.tex"
    doc = LatexDocument(source="\\documentclass{article}", output_path=tex_path)

    result = compiler.compile(doc, tmp_path)

    assert result.path == tex_path
    logger.info("PDF compiler path test completed")


def test_pdf_compiler_engine_is_none(tmp_path: Path) -> None:
    """The engine field should be 'none' since no real TeX engine is invoked."""
    compiler = PassThroughPdfCompiler()
    doc = LatexDocument(source="\\documentclass{article}", output_path=tmp_path / "exam.tex")

    result = compiler.compile(doc, tmp_path)

    assert result.engine == "none"
    logger.info("PDF compiler engine label test completed")


def test_pdf_compiler_fallback_when_output_path_is_none(tmp_path: Path) -> None:
    """When output_path is None the adapter should fall back to workspace_path / output.pdf."""
    compiler = PassThroughPdfCompiler()
    doc = LatexDocument(source="\\documentclass{article}", output_path=None)

    result = compiler.compile(doc, tmp_path)

    assert result.path == tmp_path / "output.pdf"
    assert result.engine == "none"
    logger.info("PDF compiler fallback path test completed")
