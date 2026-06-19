"""Concrete offline PaddleOCR text recognizer."""

from collections.abc import Callable
from pathlib import Path
from typing import Any
import logging
import os
import time

import cv2
import numpy as np

from new_latex_app.domain.entities import DocumentRegion, PageImage, RecognizedContent
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError

logger: logging.Logger = logging.getLogger(__name__)

OcrEngineFactory = Callable[[], Any]


class PaddleOcrTextRecognizer:
    """Run PaddleOCR on text layout regions without exposing engine internals."""

    def __init__(self, engine_factory: OcrEngineFactory | None = None) -> None:
        """Create a lazy PaddleOCR recognizer."""
        self._engine_factory = engine_factory or self._default_engine_factory
        self._engine: Any | None = None

    def recognize(
        self,
        pages: tuple[PageImage, ...],
        regions: tuple[DocumentRegion, ...],
        workspace_path: Path,
    ) -> tuple[RecognizedContent, ...]:
        """Implement the existing model-router signature for pipeline integration."""
        return self.recognize_text(pages=pages, regions=regions, workspace_path=workspace_path)

    def recognize_text(
        self,
        pages: tuple[PageImage, ...],
        regions: tuple[DocumentRegion, ...],
        workspace_path: Path,
    ) -> tuple[RecognizedContent, ...]:
        """Recognize text from regions classified as text."""
        started_at = time.perf_counter()
        logger.info("OCR recognition started")
        self._validate_workspace(workspace_path)
        page_index = {page.page_number: page for page in pages}
        text_regions = tuple(region for region in regions if region.region_type is RegionType.TEXT)
        if not text_regions:
            logger.info("OCR recognition completed in %.3fs", time.perf_counter() - started_at)
            return ()

        engine = self._get_engine()
        results: list[RecognizedContent] = []
        for region in text_regions:
            page = page_index.get(region.page_number)
            if page is None:
                raise PipelineStageError("OCR region references a missing page")
            crop = self._crop_region(page, region)
            text, confidence = self._run_ocr(engine, crop)
            results.append(
                RecognizedContent(
                    region=region,
                    text=text,
                    latex=None,
                    asset_path=None,
                    metadata={
                        "recognizer": "paddleocr",
                        "confidence": confidence,
                    },
                )
            )

        logger.info("OCR recognition completed in %.3fs", time.perf_counter() - started_at)
        return tuple(results)

    def _validate_workspace(self, workspace_path: Path) -> None:
        """Validate that the temporary workspace exists."""
        if not workspace_path.exists() or not workspace_path.is_dir():
            raise FileNotFoundError("Workspace path does not exist")

    def _get_engine(self) -> Any:
        """Lazily initialize PaddleOCR and wrap initialization failures."""
        if self._engine is not None:
            return self._engine
        try:
            self._engine = self._engine_factory()
            return self._engine
        except FileNotFoundError as error:
            logger.warning("PaddleOCR model files are missing")
            raise PipelineStageError("PaddleOCR model files are missing") from error
        except Exception as error:
            logger.warning("PaddleOCR initialization failed")
            raise PipelineStageError("PaddleOCR initialization failed") from error

    def _default_engine_factory(self) -> Any:
        """Create a PaddleOCR engine configured for local/offline model directories."""
        from paddleocr import PaddleOCR

        required_model_dirs = {
            "text_detection_model_dir": os.getenv("PADDLEOCR_TEXT_DETECTION_MODEL_DIR"),
            "text_recognition_model_dir": os.getenv("PADDLEOCR_TEXT_RECOGNITION_MODEL_DIR"),
        }
        for name, value in required_model_dirs.items():
            if value is None or not Path(value).exists():
                raise FileNotFoundError(f"Missing PaddleOCR model directory: {name}")
        return PaddleOCR(
            lang="en",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            **required_model_dirs,
        )

    def _crop_region(self, page: PageImage, region: DocumentRegion) -> np.ndarray:
        """Crop a text region from its source page image."""
        if not page.path.exists() or not page.path.is_file():
            raise FileNotFoundError("OCR page image file not found")
        image = cv2.imread(str(page.path), cv2.IMREAD_COLOR)
        if image is None:
            raise PipelineStageError("OCR page image is invalid or unreadable")
        if image.size == 0 or image.shape[0] == 0 or image.shape[1] == 0:
            raise PipelineStageError("OCR page image is empty")

        height, width = image.shape[:2]
        left = max(0, int(round(region.bbox.x)))
        top = max(0, int(round(region.bbox.y)))
        right = min(width, int(round(region.bbox.x + region.bbox.width)))
        bottom = min(height, int(round(region.bbox.y + region.bbox.height)))
        if right <= left or bottom <= top:
            raise PipelineStageError("OCR region is empty")

        crop = image[top:bottom, left:right]
        if crop.size == 0:
            raise PipelineStageError("OCR region is empty")
        return crop

    def _run_ocr(self, engine: Any, crop: np.ndarray) -> tuple[str, float | None]:
        """Run OCR and normalize PaddleOCR outputs into text and confidence."""
        try:
            raw_result = self._call_engine(engine, crop)
            words = self._extract_words(raw_result)
        except Exception as error:
            logger.warning("PaddleOCR runtime failed")
            raise PipelineStageError("PaddleOCR runtime failed") from error

        text = " ".join(word for word, _ in words).strip()
        confidences = [confidence for _, confidence in words if confidence is not None]
        average_confidence = sum(confidences) / len(confidences) if confidences else None
        return text, average_confidence

    def _call_engine(self, engine: Any, crop: np.ndarray) -> Any:
        """Call the installed PaddleOCR API variant."""
        if hasattr(engine, "ocr"):
            return engine.ocr(crop)
        if hasattr(engine, "predict"):
            return engine.predict(crop)
        raise PipelineStageError("PaddleOCR engine does not expose a supported OCR method")

    def _extract_words(self, raw_result: Any) -> list[tuple[str, float | None]]:
        """Extract recognized words from common PaddleOCR result formats."""
        words: list[tuple[str, float | None]] = []
        self._walk_result(raw_result, words)
        return words

    def _walk_result(self, value: Any, words: list[tuple[str, float | None]]) -> None:
        """Recursively collect text-confidence pairs from PaddleOCR output."""
        if isinstance(value, dict):
            self._extract_from_mapping(value, words)
            return
        if isinstance(value, tuple) and len(value) >= 2 and isinstance(value[0], str):
            words.append((value[0], self._to_confidence(value[1])))
            return
        if isinstance(value, list):
            if len(value) >= 2 and isinstance(value[1], tuple) and len(value[1]) >= 1:
                text_value = value[1][0]
                if isinstance(text_value, str):
                    confidence = self._to_confidence(value[1][1]) if len(value[1]) >= 2 else None
                    words.append((text_value, confidence))
                    return
            for item in value:
                self._walk_result(item, words)

    def _extract_from_mapping(self, value: dict[str, Any], words: list[tuple[str, float | None]]) -> None:
        """Extract OCR data from PaddleOCR mapping-style results."""
        texts = value.get("rec_texts") or value.get("texts")
        scores = value.get("rec_scores") or value.get("scores")
        if isinstance(texts, list):
            for index, text_value in enumerate(texts):
                if isinstance(text_value, str):
                    score = scores[index] if isinstance(scores, list) and index < len(scores) else None
                    words.append((text_value, self._to_confidence(score)))
            return
        for nested in value.values():
            self._walk_result(nested, words)

    def _to_confidence(self, value: Any) -> float | None:
        """Convert confidence values to floats when possible."""
        if isinstance(value, (int, float)):
            return float(value)
        return None
