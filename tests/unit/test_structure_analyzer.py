"""Unit tests for document structure analysis."""

from pathlib import Path
import logging

import pytest

from new_latex_app.domain.entities import BoundingBox, DocumentRegion, PageImage, RecognizedContent
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError
from new_latex_app.infrastructure.adapters.structure_analyzer import MetadataDocumentStructureAnalyzer

logger: logging.Logger = logging.getLogger(__name__)


def _page(page_number: int = 1) -> PageImage:
    """Create a test page image reference."""
    return PageImage(page_number=page_number, path=Path(f"page-{page_number}.png"), width=800, height=1000)


def _region(
    reading_order: int,
    region_type: RegionType = RegionType.TEXT,
    question_id: str = "page-1-question-1",
    question_index: int = 1,
    y: float | None = None,
    page_number: int = 1,
) -> DocumentRegion:
    """Create a segmented test region."""
    return DocumentRegion(
        page_number=page_number,
        region_type=region_type,
        bbox=BoundingBox(x=20.0, y=float(y if y is not None else reading_order * 30), width=220.0, height=22.0),
        confidence=0.9,
        metadata={
            "reading_order": reading_order,
            "question_id": question_id,
            "question_page_number": page_number,
            "question_index": question_index,
            "question_region_index": reading_order,
            "question_region_count": 1,
        },
    )


def _content(region: DocumentRegion, text: str | None = None, latex: str | None = None) -> RecognizedContent:
    """Create recognized content for a test region."""
    return RecognizedContent(region=region, text=text, latex=latex)


def test_analyze_single_structured_question() -> None:
    """A single segmented question should be represented by reference metadata."""
    text_region = _region(1)
    content = _content(text_region, text="Find x.")

    structure = MetadataDocumentStructureAnalyzer().analyze((_page(),), (content,))

    assert structure.contents == (content,)
    assert structure.regions == (text_region,)
    assert structure.metadata["question_count"] == 1
    assert structure.metadata["questions"][0]["content_indices"] == (0,)
    assert structure.metadata["questions"][0]["text_content_indices"] == (0,)


def test_analyze_multiple_structured_questions_preserves_reading_order() -> None:
    """Multiple questions should be ordered by segmented question metadata."""
    second = _content(_region(3, question_id="page-1-question-2", question_index=2), text="Second")
    first = _content(_region(1, question_id="page-1-question-1", question_index=1), text="First")

    structure = MetadataDocumentStructureAnalyzer().analyze((_page(),), (second, first))

    questions = structure.metadata["questions"]
    assert [question["question_id"] for question in questions] == ["page-1-question-1", "page-1-question-2"]
    assert questions[0]["content_indices"] == (1,)
    assert questions[1]["content_indices"] == (0,)


def test_analyze_question_containing_formula() -> None:
    """Formula content should be associated by Math OCR content reference."""
    text = _content(_region(1), text="Solve")
    formula = _content(_region(2, RegionType.FORMULA), latex="x^2 + 1")

    structure = MetadataDocumentStructureAnalyzer().analyze((_page(),), (text, formula))

    question = structure.metadata["questions"][0]
    assert question["content_indices"] == (0, 1)
    assert question["formula_content_indices"] == (1,)
    assert structure.contents[1].latex == "x^2 + 1"


def test_analyze_question_containing_figure_and_table_regions() -> None:
    """Figure and table regions should be associated without OCR mutation."""
    text = _content(_region(1), text="Use the figure.")
    figure = _content(_region(2, RegionType.FIGURE))
    table = _content(_region(3, RegionType.TABLE))

    structure = MetadataDocumentStructureAnalyzer().analyze((_page(),), (text, figure, table))

    question = structure.metadata["questions"][0]
    assert question["figure_region_indices"] == (1,)
    assert question["table_region_indices"] == (2,)
    assert structure.contents[1].text is None
    assert structure.contents[2].latex is None


def test_analyze_missing_ocr_content_keeps_region_reference() -> None:
    """Missing recognized text should not remove the text region reference."""
    missing_text = _content(_region(1), text=None)

    structure = MetadataDocumentStructureAnalyzer().analyze((_page(),), (missing_text,))

    question = structure.metadata["questions"][0]
    assert question["text_content_indices"] == (0,)
    assert structure.contents[0].text is None


def test_analyze_empty_document_is_rejected() -> None:
    """Empty documents should be rejected."""
    with pytest.raises(PipelineStageError, match="empty document"):
        MetadataDocumentStructureAnalyzer().analyze((), ())


def test_analyze_missing_question_group_is_rejected() -> None:
    """Content without question segmentation metadata should be rejected."""
    region = DocumentRegion(
        page_number=1,
        region_type=RegionType.TEXT,
        bbox=BoundingBox(x=20.0, y=30.0, width=220.0, height=22.0),
        metadata={"reading_order": 1},
    )

    with pytest.raises(PipelineStageError, match="question group"):
        MetadataDocumentStructureAnalyzer().analyze((_page(),), (_content(region, text="Text"),))
