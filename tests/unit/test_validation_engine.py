"""Unit tests for the pass-through validation engine adapter."""

from pathlib import Path
import logging

from new_latex_app.domain.entities import LatexDocument
from new_latex_app.infrastructure.adapters.validation_engine import PassThroughValidationEngine

logger: logging.Logger = logging.getLogger(__name__)


def test_validation_engine_passes_through_document() -> None:
    """The validation engine should return the exact same LatexDocument instance."""
    engine = PassThroughValidationEngine()
    original_doc = LatexDocument(source="\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}", output_path=Path("dummy_path.tex"))

    validated_doc = engine.validate(original_doc)

    logger.info("Validation engine test completed")
    # Verify exact object identity
    assert validated_doc is original_doc
    assert validated_doc.source == original_doc.source
    assert validated_doc.output_path == original_doc.output_path
