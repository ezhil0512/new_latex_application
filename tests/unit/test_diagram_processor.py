"""Unit tests for the diagram asset processor."""

from pathlib import Path
import logging

import cv2
import numpy as np
import pytest

from new_latex_app.domain.entities import BoundingBox, DocumentRegion, PageImage
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError
from new_latex_app.infrastructure.adapters.diagram_processor import DiagramAssetProcessor

logger: logging.Logger = logging.getLogger(__name__)


def _create_page_image(tmp_path: Path, page_number: int = 1, width: int = 200, height: int = 100) -> PageImage:
    image_path = tmp_path / f"page_{page_number}.png"
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    assert cv2.imwrite(str(image_path), image)
    return PageImage(page_number=page_number, path=image_path, width=width, height=height, dpi=300)


def _create_region(
    page_number: int,
    region_type: RegionType,
    x: float,
    y: float,
    width: float,
    height: float,
    reading_order: int,
    question_id: str,
    question_page_number: int,
    question_index: int,
) -> DocumentRegion:
    return DocumentRegion(
        page_number=page_number,
        region_type=region_type,
        bbox=BoundingBox(x=x, y=y, width=width, height=height),
        metadata={
            "reading_order": reading_order,
            "question_id": question_id,
            "question_page_number": question_page_number,
            "question_index": question_index,
        },
    )


def test_process_single_diagram(tmp_path: Path) -> None:
    """A single figure region should be staged as a diagram asset."""
    page = _create_page_image(tmp_path, page_number=1, width=120, height=80)
    region = _create_region(
        page_number=1,
        region_type=RegionType.FIGURE,
        x=10,
        y=10,
        width=80,
        height=40,
        reading_order=1,
        question_id="q1",
        question_page_number=1,
        question_index=1,
    )

    processor = DiagramAssetProcessor()
    contents = processor.recognize((page,), (region,), tmp_path)

    assert len(contents) == 1
    asset = contents[0]
    assert asset.asset_path is not None
    assert asset.asset_path.exists()
    assert asset.region == region
    assert asset.text is None
    assert asset.latex is None
    assert asset.metadata["asset_id"]
    assert asset.metadata["page_number"] == 1
    assert asset.metadata["parent_question_id"] == "q1"
    assert asset.metadata["region_reference"].startswith("figure:1:")
    assert asset.metadata["width"] == 80
    assert asset.metadata["height"] == 40


def test_process_multiple_diagrams(tmp_path: Path) -> None:
    """Multiple diagram regions should each produce a unique staged asset."""
    page = _create_page_image(tmp_path, page_number=1, width=200, height=120)
    regions = (
        _create_region(1, RegionType.FIGURE, 10, 10, 50, 30, 1, "q1", 1, 1),
        _create_region(1, RegionType.GRAPH, 70, 10, 80, 40, 2, "q1", 1, 1),
    )

    processor = DiagramAssetProcessor()
    contents = processor.recognize((page,), regions, tmp_path)

    assert len(contents) == 2
    assert contents[0].asset_path != contents[1].asset_path
    assert contents[0].metadata["asset_id"] != contents[1].metadata["asset_id"]
    assert contents[0].metadata["region_type"] == RegionType.FIGURE.value
    assert contents[1].metadata["region_type"] == RegionType.GRAPH.value


def test_process_graph_region(tmp_path: Path) -> None:
    """Graph regions should be preserved and staged like other diagrams."""
    page = _create_page_image(tmp_path, page_number=2, width=180, height=90)
    region = _create_region(2, RegionType.GRAPH, 20, 15, 100, 50, 5, "q2", 2, 1)

    processor = DiagramAssetProcessor()
    contents = processor.recognize((page,), (region,), tmp_path)

    assert len(contents) == 1
    assert contents[0].metadata["parent_question_id"] == "q2"
    assert contents[0].metadata["question_page_number"] == 2
    assert contents[0].metadata["question_index"] == 1
    assert contents[0].metadata["reading_order"] == 5


def test_process_missing_image_raises(tmp_path: Path) -> None:
    """Missing page image should fail with a pipeline stage error."""
    page = PageImage(page_number=1, path=tmp_path / "missing.png", width=100, height=100, dpi=300)
    region = _create_region(1, RegionType.FIGURE, 0, 0, 50, 50, 1, "q1", 1, 1)

    processor = DiagramAssetProcessor()
    with pytest.raises(PipelineStageError, match="page image file not found"):
        processor.recognize((page,), (region,), tmp_path)


def test_process_empty_document_returns_no_content(tmp_path: Path) -> None:
    """An empty document should return no diagram assets instead of failing."""
    page = _create_page_image(tmp_path, page_number=1)

    processor = DiagramAssetProcessor()
    contents = processor.recognize((page,), (), tmp_path)

    assert contents == ()


def test_process_workspace_failure_raises(tmp_path: Path) -> None:
    """Nonexistent workspace path should raise a pipeline stage error."""
    page = _create_page_image(tmp_path, page_number=1)
    region = _create_region(1, RegionType.FIGURE, 0, 0, 50, 50, 1, "q1", 1, 1)

    processor = DiagramAssetProcessor()
    missing_workspace = tmp_path / "missing_workspace"

    with pytest.raises(PipelineStageError, match="Workspace path does not exist"):
        processor.recognize((page,), (region,), missing_workspace)
