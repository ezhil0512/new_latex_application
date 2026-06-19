"""Unit tests for the PaddleOCR text recognizer adapter."""

from pathlib import Path
import logging

import cv2
import numpy as np
import pytest

from new_latex_app.domain.entities import BoundingBox, DocumentRegion, PageImage
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError
from new_latex_app.infrastructure.adapters.paddle_ocr import PaddleOcrTextRecognizer

logger: logging.Logger = logging.getLogger(__name__)


class _FakeOcrEngine:
    """Fake PaddleOCR engine for unit tests."""

    def __init__(self, result: object) -> None:
        """Create a fake engine."""
        self.result = result

    def ocr(self, image: np.ndarray) -> object:
        """Return a fixed OCR result."""
        assert image.size > 0
        return self.result


def _write_page(path: Path) -> None:
    """Write a simple page image."""
    image = np.full((100, 180, 3), 255, dtype=np.uint8)
    cv2.putText(image, "Hello", (20, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    assert cv2.imwrite(str(path), image)


def _text_region() -> DocumentRegion:
    """Create a text region."""
    return DocumentRegion(
        page_number=1,
        region_type=RegionType.TEXT,
        bbox=BoundingBox(x=10, y=20, width=150, height=50),
        confidence=0.9,
        metadata={"reading_order": 1},
    )


def test_recognize_normal_text_region(tmp_path: Path) -> None:
    """Text regions should be recognized and returned as RecognizedContent."""
    page_path = tmp_path / "page.png"
    _write_page(page_path)
    recognizer = PaddleOcrTextRecognizer(
        engine_factory=lambda: _FakeOcrEngine([[None, ("Hello world", 0.91)]])
    )

    results = recognizer.recognize_text(
        pages=(PageImage(page_number=1, path=page_path, width=180, height=100),),
        regions=(_text_region(),),
        workspace_path=tmp_path,
    )

    assert len(results) == 1
    assert results[0].region == _text_region()
    assert results[0].text == "Hello world"
    assert results[0].metadata["confidence"] == pytest.approx(0.91)


def test_non_text_regions_are_skipped(tmp_path: Path) -> None:
    """Only text regions should be sent to OCR."""
    page_path = tmp_path / "page.png"
    _write_page(page_path)
    recognizer = PaddleOcrTextRecognizer(engine_factory=lambda: _FakeOcrEngine([]))
    table_region = DocumentRegion(
        page_number=1,
        region_type=RegionType.TABLE,
        bbox=BoundingBox(x=10, y=20, width=150, height=50),
    )

    results = recognizer.recognize_text(
        pages=(PageImage(page_number=1, path=page_path, width=180, height=100),),
        regions=(table_region,),
        workspace_path=tmp_path,
    )

    assert results == ()


def test_empty_region_is_rejected(tmp_path: Path) -> None:
    """Empty OCR regions should be rejected."""
    page_path = tmp_path / "page.png"
    _write_page(page_path)
    recognizer = PaddleOcrTextRecognizer(engine_factory=lambda: _FakeOcrEngine([]))
    empty_region = DocumentRegion(
        page_number=1,
        region_type=RegionType.TEXT,
        bbox=BoundingBox(x=10, y=20, width=0, height=50),
    )

    with pytest.raises(PipelineStageError, match="empty"):
        recognizer.recognize_text(
            pages=(PageImage(page_number=1, path=page_path, width=180, height=100),),
            regions=(empty_region,),
            workspace_path=tmp_path,
        )


def test_invalid_image_is_rejected(tmp_path: Path) -> None:
    """Invalid page images should be rejected."""
    page_path = tmp_path / "invalid.png"
    page_path.write_bytes(b"not an image")
    recognizer = PaddleOcrTextRecognizer(engine_factory=lambda: _FakeOcrEngine([]))

    with pytest.raises(PipelineStageError, match="invalid|unreadable"):
        recognizer.recognize_text(
            pages=(PageImage(page_number=1, path=page_path, width=180, height=100),),
            regions=(_text_region(),),
            workspace_path=tmp_path,
        )


def test_ocr_initialization_failure_is_wrapped(tmp_path: Path) -> None:
    """OCR initialization failures should use the project exception hierarchy."""
    page_path = tmp_path / "page.png"
    _write_page(page_path)

    def failing_factory() -> object:
        raise RuntimeError("boom")

    recognizer = PaddleOcrTextRecognizer(engine_factory=failing_factory)

    with pytest.raises(PipelineStageError, match="initialization"):
        recognizer.recognize_text(
            pages=(PageImage(page_number=1, path=page_path, width=180, height=100),),
            regions=(_text_region(),),
            workspace_path=tmp_path,
        )
