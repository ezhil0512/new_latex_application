"""Unit tests for the visual layout detector adapter."""

from pathlib import Path
import logging

import cv2
import numpy as np
import pytest

from new_latex_app.domain.entities import PageImage
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError
from new_latex_app.infrastructure.adapters.layout_detector import OpenCvLayoutDetector

logger: logging.Logger = logging.getLogger(__name__)


def _write_page(path: Path, image: np.ndarray) -> None:
    """Write a synthetic page image."""
    assert cv2.imwrite(str(path), image)


def test_detect_normal_document_text_region(tmp_path: Path) -> None:
    """A normal document-like page should produce text layout regions."""
    page_path = tmp_path / "normal.png"
    image = np.full((300, 240), 255, dtype=np.uint8)
    for index in range(6):
        y = 40 + index * 26
        cv2.rectangle(image, (24, y), (210, y + 8), 0, -1)
    _write_page(page_path, image)

    regions = OpenCvLayoutDetector().detect((PageImage(1, page_path, 240, 300),))

    assert regions
    assert regions[0].region_type == RegionType.TEXT
    assert regions[0].metadata["reading_order"] == 1


def test_detect_blank_page_returns_no_regions(tmp_path: Path) -> None:
    """A blank page should not produce hallucinated regions."""
    page_path = tmp_path / "blank.png"
    image = np.full((200, 200), 255, dtype=np.uint8)
    _write_page(page_path, image)

    regions = OpenCvLayoutDetector().detect((PageImage(1, page_path, 200, 200),))

    assert regions == ()


def test_detect_document_containing_table(tmp_path: Path) -> None:
    """A table-like grid should be classified as a table region."""
    page_path = tmp_path / "table.png"
    image = np.full((260, 260), 255, dtype=np.uint8)
    for x in (40, 100, 160, 220):
        cv2.line(image, (x, 50), (x, 190), 0, 2)
    for y in (50, 90, 130, 170, 190):
        cv2.line(image, (40, y), (220, y), 0, 2)
    _write_page(page_path, image)

    regions = OpenCvLayoutDetector().detect((PageImage(1, page_path, 260, 260),))

    assert any(region.region_type == RegionType.TABLE for region in regions)


def test_detect_document_containing_diagram(tmp_path: Path) -> None:
    """A simple diagram-like shape should be classified as a figure region."""
    page_path = tmp_path / "diagram.png"
    image = np.full((260, 260), 255, dtype=np.uint8)
    cv2.circle(image, (130, 120), 55, 0, 3)
    cv2.arrowedLine(image, (75, 120), (185, 120), 0, 2)
    cv2.arrowedLine(image, (130, 65), (130, 175), 0, 2)
    _write_page(page_path, image)

    regions = OpenCvLayoutDetector().detect((PageImage(1, page_path, 260, 260),))

    assert any(region.region_type == RegionType.FIGURE for region in regions)


def test_detect_document_containing_mathematical_region(tmp_path: Path) -> None:
    """A visual formula block with a fraction bar should be classified as formula."""
    page_path = tmp_path / "formula.png"
    image = np.full((180, 360), 255, dtype=np.uint8)
    cv2.putText(image, "x + y", (95, 65), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
    cv2.line(image, (80, 90), (250, 90), 0, 2)
    cv2.putText(image, "z", (150, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
    _write_page(page_path, image)

    regions = OpenCvLayoutDetector().detect((PageImage(1, page_path, 360, 180),))

    assert any(region.region_type == RegionType.FORMULA for region in regions)


def test_detect_invalid_page_is_rejected(tmp_path: Path) -> None:
    """An invalid page image should be rejected."""
    page_path = tmp_path / "invalid.png"
    page_path.write_bytes(b"not an image")

    with pytest.raises(PipelineStageError, match="invalid|unreadable"):
        OpenCvLayoutDetector().detect((PageImage(1, page_path, 100, 100),))
