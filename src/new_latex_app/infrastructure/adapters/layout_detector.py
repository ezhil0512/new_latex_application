"""Concrete offline visual layout detector."""

from dataclasses import dataclass
import logging
import time

import cv2
import numpy as np

from new_latex_app.domain.entities import BoundingBox, DocumentRegion, PageImage
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError

logger: logging.Logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _CandidateRegion:
    """Internal visual region candidate."""

    x: int
    y: int
    width: int
    height: int
    area: int


class OpenCvLayoutDetector:
    """Detect coarse visual document layout regions without OCR."""

    def __init__(
        self,
        min_region_area_ratio: float = 0.0008,
        blank_foreground_ratio: float = 0.0005,
    ) -> None:
        """Create a conservative visual layout detector."""
        if min_region_area_ratio <= 0:
            raise ValueError("Minimum region area ratio must be positive")
        if blank_foreground_ratio < 0:
            raise ValueError("Blank foreground ratio must not be negative")
        self._min_region_area_ratio = min_region_area_ratio
        self._blank_foreground_ratio = blank_foreground_ratio

    def detect(self, pages: tuple[PageImage, ...]) -> tuple[DocumentRegion, ...]:
        """Return detected visual layout regions in reading order."""
        started_at = time.perf_counter()
        logger.info("Layout detection started")
        if not pages:
            raise PipelineStageError("No page images were provided for layout detection")

        regions: list[DocumentRegion] = []
        for page in pages:
            regions.extend(self._detect_page(page))

        ordered = sorted(regions, key=lambda region: (region.page_number, region.bbox.y, region.bbox.x))
        result = tuple(self._with_reading_order(region, index + 1) for index, region in enumerate(ordered))
        logger.info("Layout detection completed in %.3fs", time.perf_counter() - started_at)
        return result

    def _detect_page(self, page: PageImage) -> list[DocumentRegion]:
        """Detect visual regions for a single page."""
        self._validate_page(page)
        try:
            grayscale = cv2.imread(str(page.path), cv2.IMREAD_GRAYSCALE)
            if grayscale is None:
                raise PipelineStageError("Page image is invalid or unreadable")
            if grayscale.size == 0 or grayscale.shape[0] == 0 or grayscale.shape[1] == 0:
                raise PipelineStageError("Page image is empty")

            foreground = self._foreground_mask(grayscale)
            if self._is_blank(foreground):
                return []

            candidates = self._find_candidates(foreground)
            return [self._candidate_to_region(page, foreground, candidate) for candidate in candidates]
        except cv2.error as error:
            logger.warning("OpenCV layout detection failed")
            raise PipelineStageError("Layout detection failed") from error
        except OSError as error:
            logger.warning("Layout detection file operation failed")
            raise PipelineStageError("Layout detection file operation failed") from error

    def _validate_page(self, page: PageImage) -> None:
        """Validate page metadata and image availability."""
        if page.page_number <= 0:
            raise PipelineStageError("Page number must be positive")
        if not page.path.exists() or not page.path.is_file():
            raise FileNotFoundError("Page image file not found")
        if page.path.stat().st_size == 0:
            raise PipelineStageError("Page image file is empty")

    def _foreground_mask(self, grayscale: np.ndarray) -> np.ndarray:
        """Create a foreground mask from a preprocessed or grayscale page."""
        blurred = cv2.GaussianBlur(grayscale, (3, 3), 0)
        _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return mask

    def _is_blank(self, foreground: np.ndarray) -> bool:
        """Return true when the page has too little foreground content."""
        foreground_ratio = float(cv2.countNonZero(foreground)) / float(foreground.size)
        return foreground_ratio < self._blank_foreground_ratio

    def _find_candidates(self, foreground: np.ndarray) -> list[_CandidateRegion]:
        """Find coarse layout candidates from connected visual content."""
        page_height, page_width = foreground.shape[:2]
        min_area = int(page_height * page_width * self._min_region_area_ratio)
        horizontal_kernel = max(15, page_width // 45)
        vertical_kernel = max(3, page_height // 220)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontal_kernel, vertical_kernel))
        grouped = cv2.dilate(foreground, kernel, iterations=1)
        contours, _ = cv2.findContours(grouped, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates: list[_CandidateRegion] = []
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            area = width * height
            if area < min_area:
                continue
            if width < 5 or height < 5:
                continue
            candidates.append(_CandidateRegion(x=x, y=y, width=width, height=height, area=area))
        return self._merge_overlapping(candidates)

    def _merge_overlapping(self, candidates: list[_CandidateRegion]) -> list[_CandidateRegion]:
        """Merge overlapping candidates caused by dense page graphics."""
        merged: list[_CandidateRegion] = []
        for candidate in sorted(candidates, key=lambda item: (item.y, item.x)):
            replacement = candidate
            remaining: list[_CandidateRegion] = []
            for existing in merged:
                if self._overlaps(existing, replacement):
                    replacement = self._union(existing, replacement)
                else:
                    remaining.append(existing)
            remaining.append(replacement)
            merged = remaining
        return sorted(merged, key=lambda item: (item.y, item.x))

    def _overlaps(self, first: _CandidateRegion, second: _CandidateRegion) -> bool:
        """Return true when two candidates overlap or nearly touch."""
        padding = 24
        return not (
            first.x + first.width + padding < second.x
            or second.x + second.width + padding < first.x
            or first.y + first.height + padding < second.y
            or second.y + second.height + padding < first.y
        )

    def _union(self, first: _CandidateRegion, second: _CandidateRegion) -> _CandidateRegion:
        """Return the bounding union of two candidates."""
        x = min(first.x, second.x)
        y = min(first.y, second.y)
        right = max(first.x + first.width, second.x + second.width)
        bottom = max(first.y + first.height, second.y + second.height)
        return _CandidateRegion(x=x, y=y, width=right - x, height=bottom - y, area=(right - x) * (bottom - y))

    def _candidate_to_region(
        self,
        page: PageImage,
        foreground: np.ndarray,
        candidate: _CandidateRegion,
    ) -> DocumentRegion:
        """Convert an internal candidate into a domain layout region."""
        roi = foreground[candidate.y : candidate.y + candidate.height, candidate.x : candidate.x + candidate.width]
        region_type, confidence, features = self._classify_visual_region(roi, candidate)
        return DocumentRegion(
            page_number=page.page_number,
            region_type=region_type,
            bbox=BoundingBox(
                x=float(candidate.x),
                y=float(candidate.y),
                width=float(candidate.width),
                height=float(candidate.height),
            ),
            confidence=confidence,
            metadata={
                "detector": "opencv_visual_layout",
                "visual_features": features,
            },
        )

    def _classify_visual_region(
        self,
        roi: np.ndarray,
        candidate: _CandidateRegion,
    ) -> tuple[RegionType, float, dict[str, float]]:
        """Classify a region using visual structure only."""
        foreground_ratio = float(cv2.countNonZero(roi)) / float(max(1, roi.size))
        horizontal_lines, vertical_lines, grid_intersections = self._line_features(roi)
        aspect_ratio = float(candidate.width) / float(max(1, candidate.height))
        contour_count = self._component_count(roi)

        features = {
            "foreground_ratio": round(foreground_ratio, 4),
            "horizontal_lines": float(horizontal_lines),
            "vertical_lines": float(vertical_lines),
            "grid_intersections": float(grid_intersections),
            "aspect_ratio": round(aspect_ratio, 4),
            "component_count": float(contour_count),
        }

        if horizontal_lines >= 3 and vertical_lines >= 2 and grid_intersections >= 6:
            return RegionType.TABLE, 0.86, features
        if (
            1 <= horizontal_lines <= 2
            and vertical_lines <= 1
            and aspect_ratio >= 2.0
            and candidate.height <= 120
            and contour_count >= 3
        ):
            return RegionType.FORMULA, 0.62, features
        if self._looks_like_figure(candidate, foreground_ratio, contour_count, horizontal_lines, vertical_lines):
            return RegionType.FIGURE, 0.68, features
        return RegionType.TEXT, 0.58, features

    def _line_features(self, roi: np.ndarray) -> tuple[int, int, int]:
        """Count prominent visual lines and their grid intersections."""
        height, width = roi.shape[:2]
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(12, width // 4), 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(12, height // 4)))
        horizontal = cv2.morphologyEx(roi, cv2.MORPH_OPEN, horizontal_kernel)
        vertical = cv2.morphologyEx(roi, cv2.MORPH_OPEN, vertical_kernel)
        horizontal_count = self._count_line_contours(horizontal, min_length=max(10, width // 5))
        vertical_count = self._count_line_contours(vertical, min_length=max(10, height // 5))
        intersections = cv2.bitwise_and(horizontal, vertical)
        intersection_count, _, stats, _ = cv2.connectedComponentsWithStats(intersections, connectivity=8)
        grid_intersections = 0
        for index in range(1, intersection_count):
            if int(stats[index, cv2.CC_STAT_AREA]) >= 2:
                grid_intersections += 1
        return horizontal_count, vertical_count, grid_intersections

    def _count_line_contours(self, image: np.ndarray, min_length: int) -> int:
        """Count line-like contours above a minimum length."""
        contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        count = 0
        for contour in contours:
            _, _, width, height = cv2.boundingRect(contour)
            if max(width, height) >= min_length:
                count += 1
        return count

    def _component_count(self, roi: np.ndarray) -> int:
        """Count foreground connected components in a region."""
        component_count, _, stats, _ = cv2.connectedComponentsWithStats(roi, connectivity=8)
        count = 0
        for index in range(1, component_count):
            area = int(stats[index, cv2.CC_STAT_AREA])
            if area >= 4:
                count += 1
        return count

    def _looks_like_figure(
        self,
        candidate: _CandidateRegion,
        foreground_ratio: float,
        contour_count: int,
        horizontal_lines: int,
        vertical_lines: int,
    ) -> bool:
        """Detect non-table graphic or diagram-like regions."""
        large_region = candidate.width >= 40 and candidate.height >= 40
        sparse_or_solid_shape = contour_count <= 5 and foreground_ratio >= 0.01
        return large_region and sparse_or_solid_shape

    def _with_reading_order(self, region: DocumentRegion, reading_order: int) -> DocumentRegion:
        """Return a region with reading-order metadata added."""
        metadata = dict(region.metadata)
        metadata["reading_order"] = reading_order
        return DocumentRegion(
            page_number=region.page_number,
            region_type=region.region_type,
            bbox=region.bbox,
            confidence=region.confidence,
            metadata=metadata,
        )
