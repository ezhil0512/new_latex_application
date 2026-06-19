"""Unit tests for the OpenCV image preprocessor adapter."""

from pathlib import Path
import logging

import cv2
import numpy as np
import pytest

from new_latex_app.domain.entities import PageImage
from new_latex_app.domain.exceptions import PipelineStageError
from new_latex_app.infrastructure.adapters.image_preprocessor import OpenCvImagePreprocessor

logger: logging.Logger = logging.getLogger(__name__)


def _write_image(path: Path, image: np.ndarray) -> None:
    """Write a test image and ensure it was created."""
    assert cv2.imwrite(str(path), image)


def test_preprocess_normal_image(tmp_path: Path) -> None:
    """A normal color document-like image should produce a processed PageImage."""
    source = tmp_path / "page.png"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    image = np.full((120, 160, 3), 255, dtype=np.uint8)
    cv2.putText(image, "Question 1", (12, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    _write_image(source, image)

    pages = OpenCvImagePreprocessor().preprocess(
        (PageImage(page_number=1, path=source, width=160, height=120, dpi=200),),
        workspace,
    )

    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert pages[0].path.is_file()
    assert pages[0].path.parent == workspace / "image_preprocessing"
    assert pages[0].width == 160
    assert pages[0].height == 120


def test_preprocess_already_clean_image(tmp_path: Path) -> None:
    """An already clean image should remain readable and keep dimensions."""
    source = tmp_path / "clean.png"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    image = np.full((80, 100), 255, dtype=np.uint8)
    cv2.rectangle(image, (10, 20), (90, 22), 0, -1)
    _write_image(source, image)

    pages = OpenCvImagePreprocessor().preprocess(
        (PageImage(page_number=1, path=source, width=100, height=80),),
        workspace,
    )

    output = cv2.imread(str(pages[0].path), cv2.IMREAD_GRAYSCALE)
    assert output is not None
    assert output.shape == (80, 100)
    assert set(np.unique(output)).issubset({0, 255})


def test_preprocess_noisy_image(tmp_path: Path) -> None:
    """A noisy image should still produce a valid thresholded output."""
    source = tmp_path / "noisy.png"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    rng = np.random.default_rng(42)
    image = rng.integers(0, 256, size=(96, 128, 3), dtype=np.uint8)
    cv2.putText(image, "A", (45, 58), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    _write_image(source, image)

    pages = OpenCvImagePreprocessor().preprocess(
        (PageImage(page_number=1, path=source, width=128, height=96),),
        workspace,
    )

    assert pages[0].path.exists()
    assert pages[0].width == 128
    assert pages[0].height == 96


def test_preprocess_empty_image_file(tmp_path: Path) -> None:
    """An empty page image file should be rejected."""
    source = tmp_path / "empty.png"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source.write_bytes(b"")

    with pytest.raises(PipelineStageError, match="empty"):
        OpenCvImagePreprocessor().preprocess(
            (PageImage(page_number=1, path=source, width=0, height=0),),
            workspace,
        )


def test_preprocess_invalid_image_file(tmp_path: Path) -> None:
    """An invalid page image file should be rejected."""
    source = tmp_path / "invalid.png"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source.write_bytes(b"not an image")

    with pytest.raises(PipelineStageError, match="invalid|unreadable"):
        OpenCvImagePreprocessor().preprocess(
            (PageImage(page_number=1, path=source, width=10, height=10),),
            workspace,
        )
