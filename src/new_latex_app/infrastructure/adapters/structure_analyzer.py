"""Concrete document structure analyzer adapter."""

from dataclasses import dataclass
import logging
import time

from new_latex_app.domain.entities import DocumentRegion, DocumentStructure, PageImage, RecognizedContent
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError

logger: logging.Logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _QuestionBucket:
    """Internal bucket of content indices for one segmented question."""

    question_id: str
    page_number: int
    question_index: int
    content_indices: tuple[int, ...]


class MetadataDocumentStructureAnalyzer:
    """Organize segmented recognition outputs into question hierarchy metadata."""

    _FIGURE_REGION_TYPES: frozenset[RegionType] = frozenset(
        {
            RegionType.FIGURE,
            RegionType.GRAPH,
            RegionType.PHYSICS_DIAGRAM,
            RegionType.CHEMICAL_STRUCTURE,
            RegionType.BIOLOGY_DIAGRAM,
        }
    )

    def analyze(
        self,
        pages: tuple[PageImage, ...],
        contents: tuple[RecognizedContent, ...],
    ) -> DocumentStructure:
        """Return a document structure that references existing OCR outputs."""
        started_at = time.perf_counter()
        logger.info("Document structure analysis started")
        if not pages:
            raise PipelineStageError("Cannot analyze an empty document")

        self._validate_pages(pages)
        self._validate_contents(contents, pages)

        ordered_contents = tuple(sorted(enumerate(contents), key=lambda item: self._sort_key(item[1].region)))
        regions = self._ordered_unique_regions(tuple(content.region for content in contents))
        buckets = self._build_question_buckets(ordered_contents)
        structured_questions = tuple(
            self._build_question_metadata(bucket, ordered_contents, contents, regions)
            for bucket in buckets
        )

        logger.info("Document structure analysis completed in %.3fs", time.perf_counter() - started_at)
        return DocumentStructure(
            title=None,
            pages=pages,
            regions=regions,
            contents=contents,
            metadata={
                "structure_analyzer": "metadata_document_structure_analyzer",
                "question_count": len(structured_questions),
                "questions": structured_questions,
            },
        )

    def _validate_pages(self, pages: tuple[PageImage, ...]) -> None:
        """Validate page metadata required for structure analysis."""
        seen_page_numbers: set[int] = set()
        for page in pages:
            if page.page_number <= 0:
                raise PipelineStageError("Page number must be positive")
            if page.page_number in seen_page_numbers:
                raise PipelineStageError("Duplicate page number in document")
            if page.width <= 0 or page.height <= 0:
                raise PipelineStageError("Invalid page dimensions")
            seen_page_numbers.add(page.page_number)

    def _validate_contents(
        self,
        contents: tuple[RecognizedContent, ...],
        pages: tuple[PageImage, ...],
    ) -> None:
        """Validate recognition outputs without changing their values."""
        valid_page_numbers = {page.page_number for page in pages}
        for content in contents:
            region = content.region
            if region.page_number not in valid_page_numbers:
                raise PipelineStageError("Recognized content references an unknown page")
            if region.bbox.width <= 0 or region.bbox.height <= 0:
                raise PipelineStageError("Recognized content has an invalid region")
            if "question_id" not in region.metadata:
                raise PipelineStageError("Recognized content is missing question group metadata")
            if not isinstance(region.metadata["question_id"], str) or not region.metadata["question_id"]:
                raise PipelineStageError("Recognized content has an invalid question group")
            if "reading_order" not in region.metadata:
                raise PipelineStageError("Recognized content is missing reading order")
            if not isinstance(region.metadata["reading_order"], (int, float)):
                raise PipelineStageError("Recognized content reading order must be numeric")
            if "question_page_number" not in region.metadata or "question_index" not in region.metadata:
                raise PipelineStageError("Recognized content has incomplete question group metadata")
            if not isinstance(region.metadata["question_page_number"], int):
                raise PipelineStageError("Question page number must be numeric")
            if not isinstance(region.metadata["question_index"], int):
                raise PipelineStageError("Question index must be numeric")

    def _ordered_unique_regions(self, regions: tuple[DocumentRegion, ...]) -> tuple[DocumentRegion, ...]:
        """Return regions once, in reading order."""
        ordered_regions = sorted(regions, key=self._sort_key)
        unique_regions: list[DocumentRegion] = []
        for region in ordered_regions:
            if region not in unique_regions:
                unique_regions.append(region)
        return tuple(unique_regions)

    def _build_question_buckets(
        self,
        ordered_contents: tuple[tuple[int, RecognizedContent], ...],
    ) -> tuple[_QuestionBucket, ...]:
        """Group ordered recognition content by segmented question metadata."""
        buckets: dict[str, list[int]] = {}
        first_content_by_question: dict[str, RecognizedContent] = {}
        for original_index, content in ordered_contents:
            question_id = content.region.metadata["question_id"]
            buckets.setdefault(question_id, []).append(original_index)
            first_content_by_question.setdefault(question_id, content)

        ordered_question_ids = sorted(
            buckets,
            key=lambda question_id: self._question_sort_key(first_content_by_question[question_id].region),
        )
        return tuple(
            _QuestionBucket(
                question_id=question_id,
                page_number=int(first_content_by_question[question_id].region.metadata["question_page_number"]),
                question_index=int(first_content_by_question[question_id].region.metadata["question_index"]),
                content_indices=tuple(buckets[question_id]),
            )
            for question_id in ordered_question_ids
        )

    def _build_question_metadata(
        self,
        bucket: _QuestionBucket,
        ordered_contents: tuple[tuple[int, RecognizedContent], ...],
        contents: tuple[RecognizedContent, ...],
        regions: tuple[DocumentRegion, ...],
    ) -> dict[str, object]:
        """Build reference-only question metadata."""
        ordered_content_indices = tuple(
            original_index
            for original_index, _content in ordered_contents
            if original_index in bucket.content_indices
        )
        ordered_regions = tuple(contents[index].region for index in ordered_content_indices)
        region_index_tuple = tuple(self._region_index(regions, region) for region in ordered_regions)
        text_content_indices = tuple(
            index for index in ordered_content_indices if contents[index].region.region_type is RegionType.TEXT
        )
        formula_content_indices = tuple(
            index for index in ordered_content_indices if contents[index].region.region_type is RegionType.FORMULA
        )
        figure_region_indices = tuple(
            self._region_index(regions, contents[index].region)
            for index in ordered_content_indices
            if contents[index].region.region_type in self._FIGURE_REGION_TYPES
        )
        table_region_indices = tuple(
            self._region_index(regions, contents[index].region)
            for index in ordered_content_indices
            if contents[index].region.region_type is RegionType.TABLE
        )

        return {
            "question_id": bucket.question_id,
            "page_number": bucket.page_number,
            "question_index": bucket.question_index,
            "content_indices": ordered_content_indices,
            "region_indices": region_index_tuple,
            "text_content_indices": text_content_indices,
            "formula_content_indices": formula_content_indices,
            "figure_region_indices": figure_region_indices,
            "table_region_indices": table_region_indices,
        }

    def _question_sort_key(self, region: DocumentRegion) -> tuple[int, int, float, float]:
        """Sort questions by segmented order and position."""
        return (
            int(region.metadata["question_page_number"]),
            int(region.metadata["question_index"]),
            region.bbox.y,
            region.bbox.x,
        )

    def _region_index(self, regions: tuple[DocumentRegion, ...], target: DocumentRegion) -> int:
        """Return the stable index for a region in the structure."""
        for index, region in enumerate(regions):
            if region == target:
                return index
        raise PipelineStageError("Structured question references an unknown region")

    def _sort_key(self, region: DocumentRegion) -> tuple[int, float, float, float]:
        """Sort regions by page, reading order, and position."""
        return (region.page_number, float(region.metadata["reading_order"]), region.bbox.y, region.bbox.x)
