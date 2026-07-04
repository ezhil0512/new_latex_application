"""Concrete offline PaddleOCR text recognizer."""

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

OcrEngineFactory = Callable[[], Any]


class PaddleOcrTextRecognizer:
    """Run PaddleOCR on text layout regions without exposing engine internals."""

    def __init__(self, engine_factory: OcrEngineFactory | None = None) -> None:
        """Create a lazy PaddleOCR recognizer."""
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
        print("[DIAGNOSTIC] OCR recognition started", flush=True)
        self._validate_workspace(workspace_path)
        page_index = {page.page_number: page for page in pages}
        text_regions = tuple(region for region in regions if region.region_type is RegionType.TEXT)
        if not text_regions:
            logger.info("OCR recognition completed in %.3fs", time.perf_counter() - started_at)
            print(f"[DIAGNOSTIC] OCR recognition completed in {time.perf_counter() - started_at:.3f}s", flush=True)
            return ()

        logger.info("Before _get_engine()")
        print("[DIAGNOSTIC] Before _get_engine()", flush=True)
        engine_start = time.perf_counter()
        engine = self._get_engine()
        engine_elapsed = time.perf_counter() - engine_start
        logger.info("After _get_engine() - initialization elapsed: %.3fs", engine_elapsed)
        print(f"[DIAGNOSTIC] After _get_engine() - initialization elapsed: {engine_elapsed:.3f}s", flush=True)

        logger.info("OCR running on %d regions", len(text_regions))
        print(f"[DIAGNOSTIC] OCR running on {len(text_regions)} regions", flush=True)
        results: list[RecognizedContent] = []
        for idx, region in enumerate(text_regions):
            page = page_index.get(region.page_number)
            if page is None:
                raise PipelineStageError("OCR region references a missing page")

            logger.info("Region %d of %d: page_number=%d (dimensions: width=%d, height=%d), bbox=(x=%.2f, y=%.2f, w=%.2f, h=%.2f)",
                        idx + 1, len(text_regions), page.page_number, page.width, page.height,
                        region.bbox.x, region.bbox.y, region.bbox.width, region.bbox.height)
            print(f"[DIAGNOSTIC] Region {idx + 1} of {len(text_regions)}: page_number={page.page_number} (dimensions: width={page.width}, height={page.height}), bbox=(x={region.bbox.x:.2f}, y={region.bbox.y:.2f}, w={region.bbox.width:.2f}, h={region.bbox.height:.2f})", flush=True)

            crop = self._crop_region(page, region)
            text, confidence, raw_words = self._run_ocr(engine, crop)
            results.append(
                RecognizedContent(
                    region=region,
                    text=text,
                    latex=None,
                    asset_path=None,
                    metadata={
                        "recognizer": "paddleocr",
                        "confidence": confidence,
                        "raw_words": raw_words,
                    },
                )
            )

        logger.info("OCR recognition completed in %.3fs", time.perf_counter() - started_at)
        print(f"[DIAGNOSTIC] OCR recognition completed in {time.perf_counter() - started_at:.3f}s", flush=True)
        return tuple(results)

    def _validate_workspace(self, workspace_path: Path) -> None:
        """Validate that the temporary workspace exists."""
        if not workspace_path.exists() or not workspace_path.is_dir():
            raise FileNotFoundError("Workspace path does not exist")

    def _get_engine(self) -> Any:
        """Lazily initialize PaddleOCR and wrap initialization failures."""
        if self._engine is not None:
            return self._engine
        with self._lock:
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
        try:
            import paddlex.inference.models.common.static_infer as static_infer
            original_get_model_paths = static_infer.get_model_paths
            def patched_get_model_paths(model_dir, *args, **kwargs):
                paths = original_get_model_paths(model_dir, *args, **kwargs)
                if "paddle" in paths:
                    model_file, params_file = paths["paddle"]
                    if Path(model_file).suffix == ".json":
                        pdmodel_file = Path(model_file).with_suffix(".pdmodel")
                        if pdmodel_file.exists():
                            paths["paddle"] = (pdmodel_file, params_file)
                return paths
            static_infer.get_model_paths = patched_get_model_paths
        except Exception as error:
            logger.warning("Failed to monkeypatch paddlex get_model_paths: %s", error)

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
            text_recognition_model_name="en_PP-OCRv5_mobile_rec",
            **required_model_dirs,
        )

    def _crop_region(self, page: PageImage, region: DocumentRegion) -> np.ndarray:
        """Crop a text region from its source page image."""
        if not page.path.exists() or not page.path.is_file():
            raise FileNotFoundError("OCR page image file not found")
        image_path = page.original_path if page.original_path and page.original_path.exists() else page.path
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
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

    def _run_ocr(self, engine: Any, crop: np.ndarray) -> tuple[str, float | None, list[dict[str, Any]]]:
        """Run OCR and normalize PaddleOCR outputs into text and confidence."""
        height, width = crop.shape[:2]
        pixel_count = width * height
        logger.info("OCR crop metrics: width=%d, height=%d, pixel_count=%d", width, height, pixel_count)
        print(f"[DIAGNOSTIC] OCR crop metrics: width={width}, height={height}, pixel_count={pixel_count}", flush=True)

        try:
            logger.info("Before engine.ocr()")
            print("[DIAGNOSTIC] Before engine.ocr()", flush=True)
            ocr_start = time.perf_counter()
            raw_result = self._call_engine(engine, crop)
            ocr_elapsed = time.perf_counter() - ocr_start
            logger.info("After engine.ocr() - inference elapsed: %.3fs", ocr_elapsed)
            print(f"[DIAGNOSTIC] After engine.ocr() - inference elapsed: {ocr_elapsed:.3f}s", flush=True)

            logger.info("Before result extraction")
            print("[DIAGNOSTIC] Before result extraction", flush=True)
            extract_start = time.perf_counter()
            words = self._extract_words(raw_result)
            text = " ".join(word for word, _ in words).strip()
            confidences = [confidence for _, confidence in words if confidence is not None]
            average_confidence = sum(confidences) / len(confidences) if confidences else None
            extract_elapsed = time.perf_counter() - extract_start
            logger.info("Result extraction elapsed: %.3fs", extract_elapsed)
            print(f"[DIAGNOSTIC] Result extraction elapsed: {extract_elapsed:.3f}s", flush=True)
            raw_words = self._extract_raw_words(raw_result)
        except Exception as error:
            logger.warning("PaddleOCR runtime failed")
            raise PipelineStageError("PaddleOCR runtime failed") from error

        return text, average_confidence, raw_words

    def _extract_raw_words(self, val: Any) -> list[dict[str, Any]]:
        """Recursively collect raw words, bounding boxes, and confidences from OCR output."""
        res = []
        if isinstance(val, (list, tuple)):
            if len(val) == 2 and isinstance(val[1], (tuple, list)) and len(val[1]) == 2 and isinstance(val[1][0], str):
                res.append({"text": val[1][0], "bbox": val[0], "confidence": float(val[1][1]) if val[1][1] is not None else None})
            else:
                for item in val:
                    res.extend(self._extract_raw_words(item))
        elif isinstance(val, dict):
            texts = val.get("rec_texts") or val.get("texts")
            if isinstance(texts, list):
                polys = val.get("rec_polys") or val.get("dt_polys") or val.get("rec_boxes") or val.get("polys") or val.get("bboxes")
                scores = val.get("rec_scores") or val.get("scores")
                for idx, text in enumerate(texts):
                    if isinstance(text, str):
                        bbox = polys[idx] if isinstance(polys, (list, tuple, np.ndarray)) and idx < len(polys) else None
                        score = scores[idx] if isinstance(scores, list) and idx < len(scores) else None
                        res.append({
                            "text": text,
                            "bbox": bbox.tolist() if hasattr(bbox, "tolist") else bbox,
                            "confidence": float(score) if score is not None else None
                        })
            else:
                text = val.get("text")
                if isinstance(text, str):
                    res.append({"text": text, "bbox": val.get("bbox") or val.get("text_region"), "confidence": float(val.get("confidence")) if val.get("confidence") is not None else None})
                else:
                    for v in val.values():
                        res.extend(self._extract_raw_words(v))
        return res

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
