"""Concrete diagram asset processor for staging extracted diagram images."""

from pathlib import Path
from uuid import UUID, uuid5
import logging
import time

import cv2
import numpy as np

from new_latex_app.domain.entities import DocumentRegion, PageImage, RecognizedContent
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError

logger: logging.Logger = logging.getLogger(__name__)


class DiagramAssetProcessor:
    """Extract diagram regions into temporary workspace assets."""

    _DIAGRAM_REGION_TYPES: frozenset[RegionType] = frozenset(
        {
            RegionType.FIGURE,
            RegionType.GRAPH,
            RegionType.PHYSICS_DIAGRAM,
            RegionType.BIOLOGY_DIAGRAM,
            RegionType.CHEMICAL_STRUCTURE,
        }
    )
    _ASSET_DIRECTORY_NAME = "diagram_assets"
    _ASSET_NAMESPACE: UUID = UUID("d8c470d8-08de-4f5d-9268-6b9824a33f56")

    def recognize(
        self,
        pages: tuple[PageImage, ...],
        regions: tuple[DocumentRegion, ...],
        workspace_path: Path,
    ) -> tuple[RecognizedContent, ...]:
        """Stage diagram regions as temporary image assets without recognition."""
        started_at = time.perf_counter()
        logger.info("Diagram asset processing started")
        self._validate_workspace(workspace_path)
        page_index = {page.page_number: page for page in pages}
        diagram_regions = tuple(region for region in regions if region.region_type in self._DIAGRAM_REGION_TYPES)
        if not diagram_regions:
            logger.info("Diagram asset processing completed in %.3fs", time.perf_counter() - started_at)
            return ()

        asset_directory = self._ensure_asset_directory(workspace_path)
        results: list[RecognizedContent] = []
        for region in diagram_regions:
            page = page_index.get(region.page_number)
            if page is None:
                raise PipelineStageError("Diagram region references a missing page")
            self._validate_region_metadata(region)
            crop = self._crop_region(page, region)
            asset_id = self._asset_id(region)
            asset_path = self._save_asset(asset_directory, asset_id, crop)
            results.append(
                RecognizedContent(
                    region=region,
                    text=None,
                    latex=None,
                    asset_path=asset_path,
                    metadata={
                        "diagram_processor": "diagram_asset_processor",
                        "asset_id": asset_id,
                        "asset_filename": asset_path.name,
                        "asset_relpath": str(asset_path.relative_to(workspace_path)),
                        "page_number": region.page_number,
                        "region_type": region.region_type.value,
                        "region_reference": self._region_reference(region),
                        "parent_question_id": region.metadata.get("question_id"),
                        "question_page_number": region.metadata.get("question_page_number"),
                        "question_index": region.metadata.get("question_index"),
                        "reading_order": region.metadata.get("reading_order"),
                        "width": region.bbox.width,
                        "height": region.bbox.height,
                    },
                )
            )

        logger.info("Diagram asset processing completed in %.3fs", time.perf_counter() - started_at)
        return tuple(results)

    def _validate_workspace(self, workspace_path: Path) -> None:
        """Validate that the temporary workspace exists and is writable."""
        if not workspace_path.exists() or not workspace_path.is_dir():
            raise PipelineStageError("Workspace path does not exist")

    def _validate_region_metadata(self, region: DocumentRegion) -> None:
        """Validate question grouping metadata needed for diagram assets."""
        if "question_id" not in region.metadata:
            raise PipelineStageError("Diagram region missing question group metadata")
        if "reading_order" not in region.metadata:
            raise PipelineStageError("Diagram region missing reading order metadata")

    def _ensure_asset_directory(self, workspace_path: Path) -> Path:
        """Create a dedicated temporary directory for diagram assets."""
        asset_directory = workspace_path / self._ASSET_DIRECTORY_NAME
        asset_directory.mkdir(parents=True, exist_ok=True)
        return asset_directory

    def _crop_region(self, page: PageImage, region: DocumentRegion) -> np.ndarray:
        """Crop a diagram region from its source page image."""
        if not page.path.exists() or not page.path.is_file():
            raise PipelineStageError("Diagram page image file not found")
        image = cv2.imread(str(page.path), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise PipelineStageError("Diagram page image is invalid or unreadable")
        if image.size == 0 or image.shape[0] == 0 or image.shape[1] == 0:
            raise PipelineStageError("Diagram page image is empty")

        image_height, image_width = image.shape[:2]
        left = max(0, int(round(region.bbox.x)))
        top = max(0, int(round(region.bbox.y)))
        right = min(image_width, int(round(region.bbox.x + region.bbox.width)))
        bottom = min(image_height, int(round(region.bbox.y + region.bbox.height)))
        if right <= left or bottom <= top:
            raise PipelineStageError("Diagram region is empty")

        crop = image[top:bottom, left:right]
        if crop.size == 0:
            raise PipelineStageError("Diagram region is empty")
        return crop

    def _asset_id(self, region: DocumentRegion) -> str:
        """Generate a deterministic UUID for a diagram asset."""
        fingerprint = (
            f"{region.region_type.value}|{region.page_number}|{region.metadata.get('question_id','')}|"
            f"{region.metadata.get('reading_order','')}|{region.bbox.x:.4f}|{region.bbox.y:.4f}|"
            f"{region.bbox.width:.4f}|{region.bbox.height:.4f}"
        )
        return str(uuid5(self._ASSET_NAMESPACE, fingerprint))

    def _region_reference(self, region: DocumentRegion) -> str:
        """Build a stable region reference string for metadata."""
        return (
            f"{region.region_type.value}:{region.page_number}:"
            f"{region.metadata.get('reading_order')}:{region.bbox.x:.4f}:"
            f"{region.bbox.y:.4f}:{region.bbox.width:.4f}:{region.bbox.height:.4f}"
        )

    def _save_asset(self, asset_directory: Path, asset_id: str, crop: np.ndarray) -> Path:
        """Write the extracted diagram crop into the temporary workspace."""
        asset_path = asset_directory / f"diagram_{asset_id}.png"
        if not cv2.imwrite(str(asset_path), crop):
            raise PipelineStageError("Failed to write diagram asset image")
        return asset_path
