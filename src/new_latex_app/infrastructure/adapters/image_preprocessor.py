"""Concrete offline image preprocessing adapter."""

from pathlib import Path
import logging
import math
import time

import cv2
import numpy as np

from new_latex_app.domain.entities import PageImage
from new_latex_app.domain.exceptions import PipelineStageError

logger: logging.Logger = logging.getLogger(__name__)


class OpenCvImagePreprocessor:
    """Preprocess document page images using conservative OpenCV operations."""

    def __init__(
        self,
        max_dimension: int = 3500,
        denoise_strength: int = 7,
        clahe_clip_limit: float = 2.0,
        deskew_angle_threshold: float = 0.3,
        deskew_max_angle: float = 10.0,
    ) -> None:
        """Create an image preprocessor with conservative defaults."""
        if max_dimension <= 0:
            raise ValueError("Maximum image dimension must be positive")
        if denoise_strength < 0:
            raise ValueError("Denoise strength must not be negative")
        self._max_dimension = max_dimension
        self._denoise_strength = denoise_strength
        self._clahe_clip_limit = clahe_clip_limit
        self._deskew_angle_threshold = deskew_angle_threshold
        self._deskew_max_angle = deskew_max_angle

    def preprocess(self, pages: tuple[PageImage, ...], workspace_path: Path) -> tuple[PageImage, ...]:
        """Return preprocessed page images stored in temporary workspace."""
        started_at = time.perf_counter()
        logger.info("Image preprocessing started")
        self._validate_workspace(workspace_path)
        if not pages:
            raise PipelineStageError("No page images were provided for preprocessing")

        output_dir = workspace_path / "image_preprocessing"
        output_dir.mkdir(parents=True, exist_ok=True)

        processed_pages = tuple(self._preprocess_page(page, output_dir) for page in pages)
        logger.info("Image preprocessing completed in %.3fs", time.perf_counter() - started_at)
        return processed_pages

    def _preprocess_page(self, page: PageImage, output_dir: Path) -> PageImage:
        """Preprocess a single page image."""
        self._validate_page(page)
        try:
            image = cv2.imread(str(page.path), cv2.IMREAD_COLOR)
            if image is None:
                raise PipelineStageError("Page image is invalid or unreadable")
            if image.size == 0 or image.shape[0] == 0 or image.shape[1] == 0:
                raise PipelineStageError("Page image is empty")

            normalized = self._normalize_color(image)
            grayscale = cv2.cvtColor(normalized, cv2.COLOR_BGR2GRAY)
            resized = self._resize_if_required(grayscale)
            denoised = self._denoise(resized)
            enhanced = self._enhance_contrast(denoised)
            deskewed = self._deskew_if_applicable(enhanced)
            thresholded = self._adaptive_threshold(deskewed)

            output_path = output_dir / f"page_{page.page_number:04d}.png"
            if not cv2.imwrite(str(output_path), thresholded):
                raise PipelineStageError("Failed to write preprocessed page image")

            height, width = thresholded.shape[:2]
            return PageImage(
                page_number=page.page_number,
                path=output_path,
                width=width,
                height=height,
                dpi=page.dpi,
            )
        except cv2.error as error:
            logger.warning("OpenCV preprocessing failed")
            raise PipelineStageError("Image preprocessing failed") from error
        except OSError as error:
            logger.warning("Image preprocessing file operation failed")
            raise PipelineStageError("Image preprocessing file operation failed") from error

    def _validate_workspace(self, workspace_path: Path) -> None:
        """Validate that the workspace exists."""
        if not workspace_path.exists() or not workspace_path.is_dir():
            raise FileNotFoundError("Workspace path does not exist")

    def _validate_page(self, page: PageImage) -> None:
        """Validate page image metadata and input file availability."""
        if page.page_number <= 0:
            raise PipelineStageError("Page number must be positive")
        if not page.path.exists() or not page.path.is_file():
            raise FileNotFoundError("Page image file not found")
        if page.path.stat().st_size == 0:
            raise PipelineStageError("Page image file is empty")

    def _normalize_color(self, image: np.ndarray) -> np.ndarray:
        """Normalize color channels without changing document content."""
        lab_image = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab_image)
        normalized_l = cv2.normalize(l_channel, None, 0, 255, cv2.NORM_MINMAX)
        return cv2.cvtColor(cv2.merge((normalized_l, a_channel, b_channel)), cv2.COLOR_LAB2BGR)

    def _resize_if_required(self, image: np.ndarray) -> np.ndarray:
        """Resize only when a page exceeds the configured maximum dimension."""
        height, width = image.shape[:2]
        largest_dimension = max(height, width)
        if largest_dimension <= self._max_dimension:
            return image
        scale = self._max_dimension / float(largest_dimension)
        new_width = max(1, int(round(width * scale)))
        new_height = max(1, int(round(height * scale)))
        return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """Reduce scanning noise with a low-strength denoiser."""
        if self._denoise_strength == 0:
            return image
        return cv2.fastNlMeansDenoising(image, None, self._denoise_strength, 7, 21)

    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Improve local contrast while limiting over-amplification."""
        clahe = cv2.createCLAHE(clipLimit=self._clahe_clip_limit, tileGridSize=(8, 8))
        return clahe.apply(image)

    def _adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """Produce a binarized page suitable for downstream layout analysis."""
        return cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )

    def _deskew_if_applicable(self, image: np.ndarray) -> np.ndarray:
        """Deskew text-like pages when a reliable small angle is detected."""
        angle = self._estimate_skew_angle(image)
        if angle is None:
            return image
        if abs(angle) < self._deskew_angle_threshold or abs(angle) > self._deskew_max_angle:
            return image

        height, width = image.shape[:2]
        center = (width / 2.0, height / 2.0)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            image,
            rotation_matrix,
            (width, height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

    def _estimate_skew_angle(self, image: np.ndarray) -> float | None:
        """Estimate the skew angle from foreground pixels."""
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        coordinates = np.column_stack(np.where(binary > 0))
        if coordinates.shape[0] < 10:
            return None
        angle = float(cv2.minAreaRect(coordinates)[-1])
        if math.isclose(angle, 0.0, abs_tol=0.01):
            return None
        if angle < -45.0:
            return -(90.0 + angle)
        return -angle
