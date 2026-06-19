"""Unit tests for the Pix2Text math OCR adapter."""

from pathlib import Path
import logging

import cv2
import numpy as np
import pytest

from new_latex_app.domain.entities import BoundingBox, DocumentRegion, PageImage
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError
from new_latex_app.infrastructure.adapters.pix2text_math_ocr import Pix2TextMathOcrRecognizer

logger: logging.Logger = logging.getLogger(__name__)


class _FakePix2TextEngine:
    """Fake Pix2Text engine for unit tests."""

    def __init__(self, result: object) -> None:
        """Create a fake engine."""
        self.result = result

    def recognize(self, image: np.ndarray) -> object:
        """Return a fixed math OCR result."""
        assert image.size > 0
        return self.result


def _write_page(path: Path) -> None:
    """Write a synthetic formula page."""
    image = np.full((120, 220, 3), 255, dtype=np.uint8)
    cv2.putText(image, "x+1", (40, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.line(image, (35, 70), (145, 70), (0, 0, 0), 2)
    cv2.putText(image, "y", (82, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    assert cv2.imwrite(str(path), image)


def _formula_region() -> DocumentRegion:
    """Create a formula region."""
    return DocumentRegion(
        page_number=1,
        region_type=RegionType.FORMULA,
        bbox=BoundingBox(x=20, y=25, width=150, height=85),
        confidence=0.8,
        metadata={"reading_order": 1},
    )


def test_recognize_normal_formula_region(tmp_path: Path) -> None:
    """Formula regions should be recognized as mathematical expressions."""
    page_path = tmp_path / "page.png"
    _write_page(page_path)
    recognizer = Pix2TextMathOcrRecognizer(
        engine_factory=lambda: _FakePix2TextEngine({"latex": "\\frac{x+1}{y}", "confidence": 0.88})
    )

    results = recognizer.recognize_math(
        pages=(PageImage(page_number=1, path=page_path, width=220, height=120),),
        regions=(_formula_region(),),
        workspace_path=tmp_path,
    )

    assert len(results) == 1
    assert results[0].region == _formula_region()
    assert results[0].latex == "\\frac{x+1}{y}"
    assert results[0].text is None
    assert results[0].metadata["confidence"] == pytest.approx(0.88)


def test_non_formula_regions_are_skipped(tmp_path: Path) -> None:
    """Only formula regions should be sent to Math OCR."""
    page_path = tmp_path / "page.png"
    _write_page(page_path)
    recognizer = Pix2TextMathOcrRecognizer(engine_factory=lambda: _FakePix2TextEngine(""))
    text_region = DocumentRegion(
        page_number=1,
        region_type=RegionType.TEXT,
        bbox=BoundingBox(x=20, y=25, width=150, height=85),
    )

    results = recognizer.recognize_math(
        pages=(PageImage(page_number=1, path=page_path, width=220, height=120),),
        regions=(text_region,),
        workspace_path=tmp_path,
    )

    assert results == ()


def test_empty_formula_region_is_rejected(tmp_path: Path) -> None:
    """Empty formula regions should be rejected."""
    page_path = tmp_path / "page.png"
    _write_page(page_path)
    recognizer = Pix2TextMathOcrRecognizer(engine_factory=lambda: _FakePix2TextEngine(""))
    empty_region = DocumentRegion(
        page_number=1,
        region_type=RegionType.FORMULA,
        bbox=BoundingBox(x=20, y=25, width=0, height=85),
    )

    with pytest.raises(PipelineStageError, match="empty"):
        recognizer.recognize_math(
            pages=(PageImage(page_number=1, path=page_path, width=220, height=120),),
            regions=(empty_region,),
            workspace_path=tmp_path,
        )


def test_invalid_image_is_rejected(tmp_path: Path) -> None:
    """Invalid page images should be rejected."""
    page_path = tmp_path / "invalid.png"
    page_path.write_bytes(b"not an image")
    recognizer = Pix2TextMathOcrRecognizer(engine_factory=lambda: _FakePix2TextEngine(""))

    with pytest.raises(PipelineStageError, match="invalid|unreadable"):
        recognizer.recognize_math(
            pages=(PageImage(page_number=1, path=page_path, width=220, height=120),),
            regions=(_formula_region(),),
            workspace_path=tmp_path,
        )


def test_math_ocr_initialization_failure_is_wrapped(tmp_path: Path) -> None:
    """Math OCR initialization failures should use the project exception hierarchy."""
    page_path = tmp_path / "page.png"
    _write_page(page_path)

    def failing_factory() -> object:
        raise RuntimeError("boom")

    recognizer = Pix2TextMathOcrRecognizer(engine_factory=failing_factory)

    with pytest.raises(PipelineStageError, match="initialization"):
        recognizer.recognize_math(
            pages=(PageImage(page_number=1, path=page_path, width=220, height=120),),
            regions=(_formula_region(),),
            workspace_path=tmp_path,
        )
