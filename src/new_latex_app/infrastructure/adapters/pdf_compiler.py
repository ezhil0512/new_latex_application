"""Concrete pass-through PDF compiler adapter."""

from pathlib import Path
import logging
import time
import subprocess
import shutil
from typing import Optional

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
        """Attempt to compile LaTeX to PDF using a local TeX engine.

        This implementation is best-effort: it will try to write the LaTeX
        source to disk (if necessary) and invoke `pdflatex` once with a
        controlled timeout. On success it returns the generated PDF path and
        engine name. On failure it logs the error and returns a safe sentinel
        `CompiledPdf` whose `path` points at the TeX source so the rest of the
        pipeline can continue.
        """
        started_at = time.perf_counter()
        logger.info("PDF compilation started (best-effort)")

        # Determine target tex file path
        target_tex: Path
        if latex_document.output_path is not None:
            target_tex = latex_document.output_path
        else:
            target_tex = workspace_path / "document.tex"

        fallback_path = workspace_path / "output.pdf" if latex_document.output_path is None else target_tex

        # Ensure workspace exists
        try:
            workspace_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            # If workspace cannot be created, fall back to returning sentinel
            logger.exception("Failed to ensure workspace path for PDF compilation")
            return CompiledPdf(path=fallback_path, engine="none")

        # Write LaTeX source to the target tex file if content is available
        try:
            if latex_document.source and (not target_tex.exists() or target_tex.stat().st_size == 0):
                target_tex.write_text(latex_document.source, encoding="utf-8")
        except Exception:
            logger.exception("Failed to write LaTeX source for PDF compilation")
            return CompiledPdf(path=fallback_path, engine="none")

        # Prepare expected PDF path (same basename, .pdf)
        pdf_path = target_tex.with_suffix(".pdf")

        # If pdflatex is not available on PATH, skip compilation gracefully
        pdflatex_cmd = shutil.which("pdflatex") or shutil.which("xelatex")
        if not pdflatex_cmd:
            logger.info("No TeX engine found on PATH; skipping PDF compilation")
            return CompiledPdf(path=fallback_path, engine="none")

        # Run pdflatex once with safe flags
        cmd = [pdflatex_cmd, "-interaction=nonstopmode", "-halt-on-error", str(target_tex.name)]

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(target_tex.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=20,
                check=False,
                text=True,
            )

            # Log a trimmed compiler output for diagnostics at debug level
            out = proc.stdout or ""
            logger.debug("pdflatex output: %s", out[:4096])

            if proc.returncode == 0 and pdf_path.exists():
                logger.info("PDF compilation succeeded: %s", pdf_path)
                logger.info("PDF compilation completed in %.3fs", time.perf_counter() - started_at)
                return CompiledPdf(path=pdf_path, engine=Path(pdflatex_cmd).name)
            else:
                logger.warning("PDF compilation failed (returncode=%s)", proc.returncode)
                return CompiledPdf(path=fallback_path, engine="none")

        except subprocess.TimeoutExpired:
            logger.warning("PDF compilation timed out")
            return CompiledPdf(path=fallback_path, engine="none")
        except Exception:
            logger.exception("Unexpected error during PDF compilation")
            return CompiledPdf(path=fallback_path, engine="none")
