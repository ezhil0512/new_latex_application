"""Concrete pass-through LaTeX validation engine."""

import logging
import time

from new_latex_app.domain.entities import LatexDocument

logger: logging.Logger = logging.getLogger(__name__)


class PassThroughValidationEngine:
    """Pass-through validation engine for offline LaTeX generation.

    This adapter satisfies the ``ValidationEngine`` contract by returning the
    supplied ``LatexDocument`` unmodified, logging performance metrics, and
    avoiding complex or slow parser-based checks.
    """

    def validate(self, latex_document: LatexDocument) -> LatexDocument:
        """Validate the generated LaTeX document."""
        started_at = time.perf_counter()
        logger.info("LaTeX validation started")
        logger.info(
            "LaTeX validation completed in %.3fs",
            time.perf_counter() - started_at,
        )
        return latex_document
