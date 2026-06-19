"""Unit tests for visual question segmentation."""

import logging

import pytest

from new_latex_app.domain.entities import BoundingBox, DocumentRegion
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError
from new_latex_app.infrastructure.adapters.question_segmenter import VisualQuestionSegmenter

logger: logging.Logger = logging.getLogger(__name__)


def _region(
    index: int,
    region_type: RegionType,
    y: float,
    height: float = 20.0,
    page_number: int = 1,
) -> DocumentRegion:
    """Create a test region with reading order metadata."""
    return DocumentRegion(
        page_number=page_number,
        region_type=region_type,
        bbox=BoundingBox(x=20.0, y=y, width=200.0, height=height),
        confidence=0.8,
        metadata={"reading_order": index},
    )


def test_segment_single_question_page() -> None:
    """A compact page should produce one question group."""
    regions = (
        _region(1, RegionType.TEXT, 20.0),
        _region(2, RegionType.TEXT, 48.0),
        _region(3, RegionType.TABLE, 80.0, height=60.0),
    )

    segmented = VisualQuestionSegmenter().segment(regions)

    question_ids = {region.metadata["question_id"] for region in segmented}
    assert len(question_ids) == 1
    assert [region.metadata["question_region_index"] for region in segmented] == [1, 2, 3]


def test_segment_multiple_question_page() -> None:
    """Large vertical gaps before text regions should start new question groups."""
    regions = (
        _region(1, RegionType.TEXT, 20.0),
        _region(2, RegionType.FIGURE, 48.0, height=50.0),
        _region(3, RegionType.TEXT, 170.0),
        _region(4, RegionType.TEXT, 198.0),
    )

    segmented = VisualQuestionSegmenter().segment(regions)

    question_ids = [region.metadata["question_id"] for region in segmented]
    assert question_ids[0] == question_ids[1]
    assert question_ids[2] == question_ids[3]
    assert question_ids[0] != question_ids[2]


def test_segment_question_with_formulas() -> None:
    """Formula regions should attach to the active question group."""
    regions = (
        _region(1, RegionType.TEXT, 20.0),
        _region(2, RegionType.FORMULA, 50.0, height=35.0),
        _region(3, RegionType.TEXT, 95.0),
    )

    segmented = VisualQuestionSegmenter().segment(regions)

    assert len({region.metadata["question_id"] for region in segmented}) == 1
    assert segmented[1].region_type is RegionType.FORMULA


def test_segment_question_with_figures() -> None:
    """Figure regions should attach to the active question group."""
    regions = (
        _region(1, RegionType.TEXT, 20.0),
        _region(2, RegionType.FIGURE, 55.0, height=80.0),
        _region(3, RegionType.TABLE, 145.0, height=60.0),
    )

    segmented = VisualQuestionSegmenter().segment(regions)

    assert len({region.metadata["question_id"] for region in segmented}) == 1
    assert {region.region_type for region in segmented} == {
        RegionType.TEXT,
        RegionType.FIGURE,
        RegionType.TABLE,
    }


def test_segment_empty_document_is_rejected() -> None:
    """Empty documents should be rejected."""
    with pytest.raises(PipelineStageError, match="empty document"):
        VisualQuestionSegmenter().segment(())


def test_segment_invalid_input_missing_reading_order_is_rejected() -> None:
    """Regions without reading order should be rejected."""
    region = DocumentRegion(
        page_number=1,
        region_type=RegionType.TEXT,
        bbox=BoundingBox(x=0.0, y=0.0, width=100.0, height=20.0),
        metadata={},
    )

    with pytest.raises(PipelineStageError, match="reading order"):
        VisualQuestionSegmenter().segment((region,))
