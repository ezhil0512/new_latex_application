"""Unit tests for the LaTeX builder adapter."""

from pathlib import Path
import logging

import pytest

from new_latex_app.domain.entities import BoundingBox, DocumentRegion, DocumentStructure, PageImage, RecognizedContent
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError
from new_latex_app.infrastructure.adapters.latex_builder import DefaultLatexBuilder

logger: logging.Logger = logging.getLogger(__name__)


def _page(page_number: int = 1) -> PageImage:
    return PageImage(page_number=page_number, path=Path(f"page-{page_number}.png"), width=800, height=1000)


def _region(region_type: RegionType, reading_order: int = 1, page_number: int = 1) -> DocumentRegion:
    return DocumentRegion(
        page_number=page_number,
        region_type=region_type,
        bbox=BoundingBox(x=10.0, y=10.0, width=200.0, height=40.0),
        metadata={"reading_order": reading_order, "question_id": "q1", "question_page_number": page_number, "question_index": 1},
    )


def _content(region: DocumentRegion, text: str | None = None, latex: str | None = None, asset_filename: str | None = None) -> RecognizedContent:
    metadata = dict(region.metadata)
    if asset_filename is not None:
        metadata["asset_filename"] = asset_filename
    return RecognizedContent(region=region, text=text, latex=latex, asset_path=None, metadata=metadata)


def _structure(contents: tuple[RecognizedContent, ...], questions: tuple[dict[str, object], ...]) -> DocumentStructure:
    return DocumentStructure(title=None, pages=(_page(),), regions=tuple(content.region for content in contents), contents=contents, metadata={"questions": questions})


def test_build_text_only_document() -> None:
    region = _region(RegionType.TEXT)
    content = _content(region, text="This is a text-only question.")
    question = {"question_id": "q1", "page_number": 1, "question_index": 1, "content_indices": (0,), "region_indices": (0,), "blocks": (({"block_type": "paragraph", "content_indices": (0,), "region_indices": (0,)},),)}
    structure = _structure((content,), (question,))

    result = DefaultLatexBuilder().build(structure, Path("/tmp"))

    assert "This is a text-only question." in result.source
    assert "\\begin{enumerate}" in result.source
    assert "\\end{enumerate}" in result.source


def test_build_document_with_formula() -> None:
    region = _region(RegionType.FORMULA)
    content = _content(region, latex="x^2 + y^2 = z^2")
    question = {"question_id": "q1", "page_number": 1, "question_index": 1, "content_indices": (0,), "region_indices": (0,), "blocks": (({"block_type": "formula", "content_indices": (0,), "region_indices": (0,)},),)}
    structure = _structure((content,), (question,))

    result = DefaultLatexBuilder().build(structure, Path("/tmp"))

    assert "x^2 + y^2 = z^2" in result.source
    assert "\\[" in result.source
    assert "\\]" in result.source


def test_build_document_with_diagram() -> None:
    region = _region(RegionType.FIGURE)
    content = _content(region, text="Figure caption.", asset_filename="diagram_123.png")
    question = {"question_id": "q1", "page_number": 1, "question_index": 1, "content_indices": (0,), "region_indices": (0,), "blocks": (({"block_type": "figure", "content_indices": (0,), "region_indices": (0,)},),)}
    structure = _structure((content,), (question,))

    result = DefaultLatexBuilder().build(structure, Path("/tmp"))

    assert "assets/diagram_123.png" in result.source
    assert "\\includegraphics" in result.source
    assert "Figure caption." in result.source


def test_build_document_with_chemistry() -> None:
    region = _region(RegionType.TEXT)
    content = _content(region, text="H2O -> H+ + OH-")
    content = RecognizedContent(region=content.region, text=content.text, latex=None, asset_path=None, metadata={**content.metadata, "chemistry": {"normalized_text": "H_2O \\rightarrow H^+ + OH^-"}})
    question = {"question_id": "q1", "page_number": 1, "question_index": 1, "content_indices": (0,), "region_indices": (0,), "blocks": (({"block_type": "paragraph", "content_indices": (0,), "region_indices": (0,)},),)}
    structure = _structure((content,), (question,))

    result = DefaultLatexBuilder().build(structure, Path("/tmp"))

    assert "H_2O" in result.source
    assert "\\rightarrow" in result.source


def test_build_empty_document_raises() -> None:
    structure = DocumentStructure(title=None, pages=(), regions=(), contents=(), metadata={})

    with pytest.raises(PipelineStageError, match="empty document"):
        DefaultLatexBuilder().build(structure, Path("/tmp"))


def test_build_missing_metadata_raises() -> None:
    region = _region(RegionType.TEXT)
    content = _content(region, text="Missing question metadata")
    structure = DocumentStructure(title=None, pages=(_page(),), regions=(region,), contents=(content,), metadata={})

    with pytest.raises(PipelineStageError, match="missing question metadata"):
        DefaultLatexBuilder().build(structure, Path("/tmp"))
