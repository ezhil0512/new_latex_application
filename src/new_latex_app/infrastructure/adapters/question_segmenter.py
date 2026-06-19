"""Concrete visual question segmentation adapter."""

from dataclasses import dataclass
import logging
import time

from new_latex_app.domain.entities import DocumentRegion
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError

logger: logging.Logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _QuestionGroup:
    """Internal question group built from layout regions."""

    question_id: str
    page_number: int
    regions: tuple[DocumentRegion, ...]


class VisualQuestionSegmenter:
    """Group visual layout regions into question-aware region metadata."""

    _ATTACHABLE_REGION_TYPES: frozenset[RegionType] = frozenset(
        {
            RegionType.TEXT,
            RegionType.FORMULA,
            RegionType.TABLE,
            RegionType.FIGURE,
            RegionType.GRAPH,
            RegionType.PHYSICS_DIAGRAM,
            RegionType.CHEMICAL_STRUCTURE,
            RegionType.BIOLOGY_DIAGRAM,
        }
    )

    def __init__(self, vertical_gap_multiplier: float = 1.8) -> None:
        """Create a visual question segmenter."""
        if vertical_gap_multiplier <= 0:
            raise ValueError("Vertical gap multiplier must be positive")
        self._vertical_gap_multiplier = vertical_gap_multiplier

    def segment(self, regions: tuple[DocumentRegion, ...]) -> tuple[DocumentRegion, ...]:
        """Return question-aware regions while preserving the existing port shape."""
        started_at = time.perf_counter()
        logger.info("Question segmentation started")
        if not regions:
            raise PipelineStageError("Cannot segment an empty document")
        self._validate_regions(regions)

        ordered_regions = tuple(sorted(regions, key=self._sort_key))
        grouped_regions: list[DocumentRegion] = []
        for page_number in sorted({region.page_number for region in ordered_regions}):
            page_regions = tuple(region for region in ordered_regions if region.page_number == page_number)
            groups = self._segment_page(page_number, page_regions)
            for question_index, group in enumerate(groups, start=1):
                for region_index, region in enumerate(group.regions, start=1):
                    grouped_regions.append(
                        self._with_question_metadata(
                            region=region,
                            group=group,
                            question_index=question_index,
                            region_index=region_index,
                            region_count=len(group.regions),
                        )
                    )

        logger.info("Question segmentation completed in %.3fs", time.perf_counter() - started_at)
        return tuple(sorted(grouped_regions, key=self._sort_key))

    def _validate_regions(self, regions: tuple[DocumentRegion, ...]) -> None:
        """Validate regions before segmentation."""
        for region in regions:
            if region.page_number <= 0:
                raise PipelineStageError("Region page number must be positive")
            if region.bbox.width <= 0 or region.bbox.height <= 0:
                raise PipelineStageError("Invalid region bounding box")
            if "reading_order" not in region.metadata:
                raise PipelineStageError("Region is missing reading order")
            if not isinstance(region.metadata["reading_order"], (int, float)):
                raise PipelineStageError("Region reading order must be numeric")

    def _segment_page(
        self,
        page_number: int,
        regions: tuple[DocumentRegion, ...],
    ) -> tuple[_QuestionGroup, ...]:
        """Segment one page using visual order and vertical spacing."""
        attachable_regions = tuple(
            region for region in regions if region.region_type in self._ATTACHABLE_REGION_TYPES
        )
        if not attachable_regions:
            return ()

        typical_height = self._typical_text_height(attachable_regions)
        groups: list[list[DocumentRegion]] = []
        current_group: list[DocumentRegion] = []
        previous_region: DocumentRegion | None = None

        for region in attachable_regions:
            if previous_region is None:
                current_group.append(region)
                previous_region = region
                continue

            if self._starts_new_question(previous_region, region, typical_height):
                groups.append(current_group)
                current_group = [region]
            else:
                current_group.append(region)
            previous_region = region

        if current_group:
            groups.append(current_group)

        return tuple(
            _QuestionGroup(
                question_id=f"page-{page_number}-question-{index + 1}",
                page_number=page_number,
                regions=tuple(group),
            )
            for index, group in enumerate(groups)
        )

    def _starts_new_question(
        self,
        previous_region: DocumentRegion,
        current_region: DocumentRegion,
        typical_height: float,
    ) -> bool:
        """Determine whether a region starts a new visual question group."""
        if current_region.region_type is not RegionType.TEXT:
            return False
        if previous_region.page_number != current_region.page_number:
            return True
        vertical_gap = current_region.bbox.y - (previous_region.bbox.y + previous_region.bbox.height)
        if vertical_gap <= 0:
            return False
        return vertical_gap >= typical_height * self._vertical_gap_multiplier

    def _typical_text_height(self, regions: tuple[DocumentRegion, ...]) -> float:
        """Estimate typical text height for visual gap grouping."""
        text_heights = sorted(
            region.bbox.height for region in regions if region.region_type is RegionType.TEXT
        )
        if not text_heights:
            return 24.0
        middle = len(text_heights) // 2
        if len(text_heights) % 2 == 1:
            return float(text_heights[middle])
        return float((text_heights[middle - 1] + text_heights[middle]) / 2.0)

    def _with_question_metadata(
        self,
        region: DocumentRegion,
        group: _QuestionGroup,
        question_index: int,
        region_index: int,
        region_count: int,
    ) -> DocumentRegion:
        """Return a region annotated with question grouping metadata."""
        metadata = dict(region.metadata)
        metadata["question_id"] = group.question_id
        metadata["question_page_number"] = group.page_number
        metadata["question_index"] = question_index
        metadata["question_region_index"] = region_index
        metadata["question_region_count"] = region_count
        metadata["question_segmentation_strategy"] = "visual_reading_order_gap"
        return DocumentRegion(
            page_number=region.page_number,
            region_type=region.region_type,
            bbox=region.bbox,
            confidence=region.confidence,
            metadata=metadata,
        )

    def _sort_key(self, region: DocumentRegion) -> tuple[int, float, float, float]:
        """Sort regions by page, reading order, and position."""
        reading_order = float(region.metadata["reading_order"])
        return (region.page_number, reading_order, region.bbox.y, region.bbox.x)
