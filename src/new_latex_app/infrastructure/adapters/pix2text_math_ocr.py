"""Concrete offline Pix2Text math OCR recognizer."""

from collections.abc import Callable
from pathlib import Path
from typing import Any
import logging
import os
import threading
import time

import cv2
import numpy as np

from new_latex_app.domain.entities import DocumentRegion, PageImage, RecognizedContent
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError

logger: logging.Logger = logging.getLogger(__name__)

MathOcrEngineFactory = Callable[[], Any]


class Pix2TextMathOcrRecognizer:
    """Run Pix2Text on formula regions without exposing Pix2Text internals."""

    def __init__(self, engine_factory: MathOcrEngineFactory | None = None) -> None:
        """Create a lazy Pix2Text recognizer."""
        self._engine_factory = engine_factory or self._default_engine_factory
        self._engine: Any | None = None
        self._lock = threading.Lock()

    def recognize(
        self,
        pages: tuple[PageImage, ...],
        regions: tuple[DocumentRegion, ...],
        workspace_path: Path,
    ) -> tuple[RecognizedContent, ...]:
        """Implement the existing model-router signature for pipeline integration."""
        return self.recognize_math(pages=pages, regions=regions, workspace_path=workspace_path)

    def recognize_math(
        self,
        pages: tuple[PageImage, ...],
        regions: tuple[DocumentRegion, ...],
        workspace_path: Path,
    ) -> tuple[RecognizedContent, ...]:
        """Recognize mathematical expressions from formula regions."""
        started_at = time.perf_counter()
        logger.info("Math OCR recognition started")
        print("[DIAGNOSTIC] Math OCR recognition started", flush=True)
        self._validate_workspace(workspace_path)
        page_index = {page.page_number: page for page in pages}
        formula_regions = tuple(region for region in regions if region.region_type is RegionType.FORMULA)
        if not formula_regions:
            logger.info("Math OCR recognition completed in %.3fs", time.perf_counter() - started_at)
            print(f"[DIAGNOSTIC] Math OCR recognition completed in {time.perf_counter() - started_at:.3f}s", flush=True)
            return ()

        logger.info("Before _get_engine()")
        print("[DIAGNOSTIC] Before _get_engine()", flush=True)
        engine_start = time.perf_counter()
        engine = self._get_engine()
        engine_elapsed = time.perf_counter() - engine_start
        logger.info("After _get_engine() - initialization elapsed: %.3fs", engine_elapsed)
        print(f"[DIAGNOSTIC] After _get_engine() - initialization elapsed: {engine_elapsed:.3f}s", flush=True)

        logger.info("Math OCR running on %d regions", len(formula_regions))
        print(f"[DIAGNOSTIC] Math OCR running on {len(formula_regions)} regions", flush=True)
        results: list[RecognizedContent] = []
        for idx, region in enumerate(formula_regions):
            page = page_index.get(region.page_number)
            if page is None:
                raise PipelineStageError("Math OCR region references a missing page")

            logger.info("Region %d of %d: page_number=%d (dimensions: width=%d, height=%d), bbox=(x=%.2f, y=%.2f, w=%.2f, h=%.2f)",
                        idx + 1, len(formula_regions), page.page_number, page.width, page.height,
                        region.bbox.x, region.bbox.y, region.bbox.width, region.bbox.height)
            print(f"[DIAGNOSTIC] Region {idx + 1} of {len(formula_regions)}: page_number={page.page_number} (dimensions: width={page.width}, height={page.height}), bbox=(x={region.bbox.x:.2f}, y={region.bbox.y:.2f}, w={region.bbox.width:.2f}, h={region.bbox.height:.2f})", flush=True)

            crop = self._crop_region(page, region)
            expression, confidence = self._run_math_ocr(engine, crop)
            results.append(
                RecognizedContent(
                    region=region,
                    text=None,
                    latex=expression,
                    asset_path=None,
                    metadata={
                        "recognizer": "pix2text",
                        "confidence": confidence,
                    },
                )
            )

        logger.info("Math OCR recognition completed in %.3fs", time.perf_counter() - started_at)
        print(f"[DIAGNOSTIC] Math OCR recognition completed in {time.perf_counter() - started_at:.3f}s", flush=True)
        return tuple(results)

    def _validate_workspace(self, workspace_path: Path) -> None:
        """Validate that the temporary workspace exists."""
        if not workspace_path.exists() or not workspace_path.is_dir():
            raise FileNotFoundError("Workspace path does not exist")

    def _get_engine(self) -> Any:
        """Lazily initialize Pix2Text and wrap initialization failures."""
        if self._engine is not None:
            return self._engine
        with self._lock:
            if self._engine is not None:
                return self._engine
            try:
                self._engine = self._engine_factory()
                return self._engine
            except FileNotFoundError as error:
                logger.warning("Pix2Text model files are missing")
                raise PipelineStageError("Pix2Text model files are missing") from error
            except Exception as error:
                logger.warning("Pix2Text initialization failed")
                raise PipelineStageError("Pix2Text initialization failed") from error


    def _default_engine_factory(self) -> Any:
        """Create a Pix2Text engine configured for local/offline model files."""
        from pix2text import Pix2Text

        model_dir = os.getenv("PIX2TEXT_MODEL_DIR")
        if model_dir is None or not Path(model_dir).exists():
            raise FileNotFoundError("Missing Pix2Text model directory: PIX2TEXT_MODEL_DIR")
        return Pix2Text.from_config(model_dir)

    def _crop_region(self, page: PageImage, region: DocumentRegion) -> np.ndarray:
        """Crop a formula region from its source page image."""
        if not page.path.exists() or not page.path.is_file():
            raise FileNotFoundError("Math OCR page image file not found")
        image_path = page.original_path if page.original_path and page.original_path.exists() else page.path
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise PipelineStageError("Math OCR page image is invalid or unreadable")
        if image.size == 0 or image.shape[0] == 0 or image.shape[1] == 0:
            raise PipelineStageError("Math OCR page image is empty")

        height, width = image.shape[:2]
        left = max(0, int(round(region.bbox.x)))
        top = max(0, int(round(region.bbox.y)))
        right = min(width, int(round(region.bbox.x + region.bbox.width)))
        bottom = min(height, int(round(region.bbox.y + region.bbox.height)))
        if right <= left or bottom <= top:
            raise PipelineStageError("Math OCR formula region is empty")

        crop = image[top:bottom, left:right]
        if crop.size == 0:
            raise PipelineStageError("Math OCR formula region is empty")
        return crop

    def _run_math_ocr(self, engine: Any, crop: np.ndarray) -> tuple[str, float | None]:
        """Run Pix2Text and normalize outputs into expression and confidence."""
        height, width = crop.shape[:2]
        pixel_count = width * height
        logger.info("Math OCR crop metrics: width=%d, height=%d, pixel_count=%d", width, height, pixel_count)
        print(f"[DIAGNOSTIC] Math OCR crop metrics: width={width}, height={height}, pixel_count={pixel_count}", flush=True)

        try:
            logger.info("Before engine.recognize()")
            print("[DIAGNOSTIC] Before engine.recognize()", flush=True)
            ocr_start = time.perf_counter()
            raw_result = self._call_engine(engine, crop)
            ocr_elapsed = time.perf_counter() - ocr_start
            logger.info("After engine.recognize() - inference elapsed: %.3fs", ocr_elapsed)
            print(f"[DIAGNOSTIC] After engine.recognize() - inference elapsed: {ocr_elapsed:.3f}s", flush=True)

            logger.info("Before result extraction")
            print("[DIAGNOSTIC] Before result extraction", flush=True)
            extract_start = time.perf_counter()
            expression, confidence = self._extract_expression(raw_result)
            extract_elapsed = time.perf_counter() - extract_start
            logger.info("Result extraction elapsed: %.3fs", extract_elapsed)
            print(f"[DIAGNOSTIC] Result extraction elapsed: {extract_elapsed:.3f}s", flush=True)
        except Exception as error:
            logger.warning("Pix2Text runtime failed")
            raise PipelineStageError("Pix2Text runtime failed") from error

        return expression.strip(), confidence

    def _call_engine(self, engine: Any, crop: np.ndarray) -> Any:
        """Call a supported Pix2Text API variant."""
        if hasattr(engine, "recognize"):
            return engine.recognize(crop)
        if hasattr(engine, "predict"):
            return engine.predict(crop)
        if callable(engine):
            return engine(crop)
        raise PipelineStageError("Pix2Text engine does not expose a supported recognition method")

    def _extract_expression(self, raw_result: Any) -> tuple[str, float | None]:
        """Extract a mathematical expression from common Pix2Text result formats."""
        if isinstance(raw_result, str):
            return raw_result, None
        if isinstance(raw_result, dict):
            expression = raw_result.get("latex") or raw_result.get("text") or raw_result.get("result")
            confidence = raw_result.get("confidence") or raw_result.get("score")
            if isinstance(expression, str):
                return expression, self._to_confidence(confidence)
            for value in raw_result.values():
                nested_expression, nested_confidence = self._extract_expression(value)
                if nested_expression:
                    return nested_expression, nested_confidence
        if isinstance(raw_result, tuple) and raw_result:
            expression, confidence = self._extract_expression(raw_result[0])
            if confidence is None and len(raw_result) > 1:
                confidence = self._to_confidence(raw_result[1])
            return expression, confidence
        if isinstance(raw_result, list):
            expressions: list[str] = []
            confidences: list[float] = []
            for item in raw_result:
                expression, confidence = self._extract_expression(item)
                if expression:
                    expressions.append(expression)
                if confidence is not None:
                    confidences.append(confidence)
            average_confidence = sum(confidences) / len(confidences) if confidences else None
            return " ".join(expressions), average_confidence
        return "", None

    def _to_confidence(self, value: Any) -> float | None:
        """Convert confidence values to floats when possible."""
        if isinstance(value, (int, float)):
            return float(value)
        return None
