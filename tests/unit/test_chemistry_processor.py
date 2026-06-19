"""Unit tests for the chemistry processor adapter."""

from pathlib import Path
import logging

import pytest

from new_latex_app.domain.entities import BoundingBox, DocumentRegion, DocumentStructure, PageImage, RecognizedContent
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError
from new_latex_app.infrastructure.adapters.chemistry_processor import MetadataChemistryProcessor

logger: logging.Logger = logging.getLogger(__name__)


def _page(page_number: int = 1) -> PageImage:
    return PageImage(page_number=page_number, path=Path(f"page-{page_number}.png"), width=800, height=1000)


def _region(reading_order: int, region_type: RegionType = RegionType.TEXT, page_number: int = 1) -> DocumentRegion:
    return DocumentRegion(
        page_number=page_number,
        region_type=region_type,
        bbox=BoundingBox(x=20.0, y=float(reading_order * 30), width=220.0, height=22.0),
        confidence=0.9,
        metadata={"reading_order": reading_order},
    )


def _content(region: DocumentRegion, text: str | None = None, latex: str | None = None) -> RecognizedContent:
    return RecognizedContent(region=region, text=text, latex=latex)


def _structure(contents: tuple[RecognizedContent, ...]) -> DocumentStructure:
    return DocumentStructure(
        title=None,
        pages=(_page(),),
        regions=tuple(content.region for content in contents),
        contents=contents,
        metadata={},
    )


def test_process_normalizes_formula_metadata() -> None:
    content = _content(_region(1), text="Fe2O3")
    structure = _structure((content,))

    result = MetadataChemistryProcessor().process(structure)

    chemistry = result.contents[0].metadata["chemistry"]
    assert chemistry["normalized_text"] == "Fe_{2}O_{3}"
    assert "subscript" in chemistry["patterns"]
    assert result.contents[0].text == "Fe2O3"


def test_process_normalizes_reaction_equations() -> None:
    content = _content(_region(1), text="2H2 + O2 -> 2H2O")
    structure = _structure((content,))

    result = MetadataChemistryProcessor().process(structure)

    chemistry = result.contents[0].metadata["chemistry"]
    assert chemistry["normalized_text"] == "2H_{2} + O_{2} \\rightarrow 2H_{2}O"
    assert "reaction_arrow" in chemistry["patterns"]


def test_process_normalizes_ionic_compounds() -> None:
    content = _content(_region(1), text="Na+ + Cl- -> NaCl")
    structure = _structure((content,))

    result = MetadataChemistryProcessor().process(structure)

    chemistry = result.contents[0].metadata["chemistry"]
    assert chemistry["normalized_text"] == "Na^{+} + Cl^{-} \\rightarrow NaCl"
    assert "ionic_charge" in chemistry["patterns"]


def test_process_normalizes_state_symbols() -> None:
    content = _content(_region(1), text="H2O(l) + NaCl(aq)")
    structure = _structure((content,))

    result = MetadataChemistryProcessor().process(structure)

    chemistry = result.contents[0].metadata["chemistry"]
    assert chemistry["normalized_text"] == "H_{2}O\\,(l) + NaCl\\,(aq)"
    assert "state_symbol" in chemistry["patterns"]


def test_process_leaves_non_chemistry_content_unchanged() -> None:
    content = _content(_region(1), text="This is not chemistry.")
    structure = _structure((content,))

    result = MetadataChemistryProcessor().process(structure)

    assert "chemistry" not in result.contents[0].metadata
    assert result.contents[0].text == "This is not chemistry."


def test_process_rejects_empty_document() -> None:
    with pytest.raises(PipelineStageError, match="empty document"):
        MetadataChemistryProcessor().process(DocumentStructure(title=None, pages=(), regions=(), contents=(), metadata={}))


def test_process_rejects_invalid_metadata_structure() -> None:
    content = _content(_region(1), text="H2O")
    structure = DocumentStructure(title=None, pages=(_page(),), regions=(content.region,), contents=(content,), metadata=None)  # type: ignore[arg-type]

    with pytest.raises(PipelineStageError, match="Invalid document metadata"):
        MetadataChemistryProcessor().process(structure)
