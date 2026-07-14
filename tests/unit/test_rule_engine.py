"""Unit tests for the rule engine adapter."""

from pathlib import Path
import logging

import pytest

from new_latex_app.domain.entities import BoundingBox, DocumentRegion, DocumentStructure, PageImage, RecognizedContent
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError
from new_latex_app.infrastructure.adapters.rule_engine import MetadataRuleEngine

logger: logging.Logger = logging.getLogger(__name__)


def _page(page_number: int = 1) -> PageImage:
    return PageImage(page_number=page_number, path=Path(f"page-{page_number}.png"), width=800, height=1000)


def _region(
    reading_order: int,
    region_type: RegionType = RegionType.TEXT,
    question_id: str = "page-1-question-1",
    question_index: int = 1,
    y: float | None = None,
    page_number: int = 1,
) -> DocumentRegion:
    return DocumentRegion(
        page_number=page_number,
        region_type=region_type,
        bbox=BoundingBox(x=20.0, y=float(y if y is not None else reading_order * 30), width=220.0, height=22.0),
        confidence=0.9,
        metadata={"reading_order": reading_order},
    )


def _content(region: DocumentRegion, text: str | None = None, latex: str | None = None) -> RecognizedContent:
    return RecognizedContent(region=region, text=text, latex=latex)


def _structure(contents: tuple[RecognizedContent, ...], regions: tuple[DocumentRegion, ...], questions: tuple[dict[str, object], ...]) -> DocumentStructure:
    return DocumentStructure(
        title=None,
        pages=(_page(),),
        regions=regions,
        contents=contents,
        metadata={"questions": questions},
    )


def test_apply_preserves_question_order() -> None:
    text = _content(_region(1), text="First question")
    formula = _content(_region(2, RegionType.FORMULA), latex="a+b")
    question = {"question_id": "page-1-question-1", "page_number": 1, "question_index": 1, "content_indices": (0, 1), "region_indices": (0, 1)}
    structure = _structure((text, formula), (text.region, formula.region), (question,))

    result = MetadataRuleEngine().apply(structure)

    assert result.metadata["question_count"] == 1
    normalized = result.metadata["questions"][0]
    assert normalized["content_indices"] == (0, 1)
    assert normalized["formula_content_indices"] == (1,)
    assert normalized["paragraph_groups"] == ((0,),)


def test_apply_groups_mcq_options() -> None:
    question = _content(_region(1, RegionType.TEXT), text="Choose")
    option_a = _content(_region(2, RegionType.OPTION), text="A")
    option_b = _content(_region(3, RegionType.OPTION), text="B")
    options = {"question_id": "page-1-question-1", "page_number": 1, "question_index": 1, "content_indices": (0, 1, 2), "region_indices": (0, 1, 2)}
    structure = _structure((question, option_a, option_b), (question.region, option_a.region, option_b.region), (options,))

    result = MetadataRuleEngine().apply(structure)

    normalized = result.metadata["questions"][0]
    assert normalized["option_content_indices"] == (1, 2)
    assert normalized["option_groups"] == ((1, 2),)
    assert normalized["blocks"][0]["block_type"] == "paragraph"
    assert normalized["blocks"][1]["block_type"] == "option_group"


def test_apply_expands_spatial_blocks_into_mcq_options() -> None:
    text = RecognizedContent(
        region=_region(1, RegionType.TEXT),
        text="Choose the correct answer.",
        metadata={
            "spatial_blocks": [
                {
                    "text": "Choose the correct answer.",
                    "bbox": [[10.0, 10.0], [210.0, 10.0], [210.0, 30.0], [10.0, 30.0]],
                },
                {
                    "text": "(a) 9.6 V",
                    "bbox": [[20.0, 60.0], [80.0, 60.0], [80.0, 80.0], [20.0, 80.0]],
                },
                {
                    "text": "(b) 2.6 V",
                    "bbox": [[220.0, 60.0], [280.0, 60.0], [280.0, 80.0], [220.0, 80.0]],
                },
            ]
        },
    )
    question = {"question_id": "page-1-question-1", "page_number": 1, "question_index": 1, "content_indices": (0,), "region_indices": (0,)}
    structure = _structure((text,), (text.region,), (question,))

    result = MetadataRuleEngine().apply(structure)

    normalized = result.metadata["questions"][0]
    assert tuple(content.text for content in result.contents) == ("Choose the correct answer.", "9.6 V", "2.6 V")
    assert tuple(content.region.region_type for content in result.contents) == (
        RegionType.TEXT,
        RegionType.OPTION,
        RegionType.OPTION,
    )
    assert normalized["content_indices"] == (0, 1, 2)
    assert normalized["text_content_indices"] == (0,)
    assert normalized["option_content_indices"] == (1, 2)
    assert normalized["option_groups"] == ((1, 2),)
    assert normalized["blocks"][0]["block_type"] == "paragraph"
    assert normalized["blocks"][1]["block_type"] == "option_group"


def test_apply_keeps_unmarked_spatial_blocks_as_paragraph() -> None:
    text = RecognizedContent(
        region=_region(1, RegionType.TEXT),
        text="Line one\nLine two",
        metadata={
            "spatial_blocks": [
                {"text": "Line one", "bbox": [[10.0, 10.0], [80.0, 10.0], [80.0, 30.0], [10.0, 30.0]]},
                {"text": "Line two", "bbox": [[10.0, 40.0], [80.0, 40.0], [80.0, 60.0], [10.0, 60.0]]},
            ]
        },
    )
    question = {"question_id": "page-1-question-1", "page_number": 1, "question_index": 1, "content_indices": (0,), "region_indices": (0,)}
    structure = _structure((text,), (text.region,), (question,))

    result = MetadataRuleEngine().apply(structure)

    normalized = result.metadata["questions"][0]
    assert result.contents == (text,)
    assert normalized["content_indices"] == (0,)
    assert normalized["option_content_indices"] == ()
    assert normalized["blocks"] == ({"block_type": "paragraph", "content_indices": (0,), "region_indices": (0,)},)


def test_apply_associates_figures_and_tables() -> None:
    question = _content(_region(1, RegionType.TEXT), text="Refer")
    figure = _content(_region(2, RegionType.FIGURE))
    table = _content(_region(3, RegionType.TABLE))
    questions = {"question_id": "page-1-question-1", "page_number": 1, "question_index": 1, "content_indices": (0, 1, 2), "region_indices": (0, 1, 2)}
    structure = _structure((question, figure, table), (question.region, figure.region, table.region), (questions,))

    result = MetadataRuleEngine().apply(structure)

    normalized = result.metadata["questions"][0]
    assert normalized["figure_region_indices"] == (1,)
    assert normalized["table_region_indices"] == (2,)


def test_apply_consumes_reconstructed_lines() -> None:
    reconstructed = [
        {"text": "Line 1 reconstructed"},
        {"text": "Line 2 reconstructed"}
    ]
    text = RecognizedContent(
        region=_region(1),
        text="Original OCR Text",
        metadata={"reconstructed_lines": reconstructed}
    )
    question = {"question_id": "page-1-question-1", "page_number": 1, "question_index": 1, "content_indices": (0,), "region_indices": (0,)}
    structure = _structure((text,), (text.region,), (question,))

    result = MetadataRuleEngine().apply(structure)
    assert result.contents[0].text == "Line 1 reconstructed\nLine 2 reconstructed"
    assert result.contents[0].metadata.get("reconstructed_lines") == reconstructed


def test_apply_rejects_empty_document() -> None:
    with pytest.raises(PipelineStageError, match="empty document structure"):
        MetadataRuleEngine().apply(DocumentStructure(title=None, pages=(), regions=(), contents=(), metadata={}))


def test_apply_rejects_invalid_question_structure() -> None:
    question = {"question_id": "", "page_number": 1, "question_index": 1, "content_indices": (), "region_indices": ()}
    content = _content(_region(1))
    structure = _structure((content,), (content.region,), (question,))

    with pytest.raises(PipelineStageError, match="missing a valid identifier"):
        MetadataRuleEngine().apply(structure)
