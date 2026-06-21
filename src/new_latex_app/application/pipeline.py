"""Pipeline orchestration skeleton."""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar
from uuid import UUID
import logging
import time

from new_latex_app.domain.entities import InputDocument, ProcessingResult
from new_latex_app.domain.enums import PipelineStageName
from new_latex_app.domain.ports.document_loader import DocumentLoader
from new_latex_app.domain.ports.latex_builder import LatexBuilder
from new_latex_app.domain.ports.layout_detection import LayoutDetector
from new_latex_app.domain.ports.chemistry_processor import ChemistryProcessor
from new_latex_app.domain.ports.export_manager import ExportManager
from new_latex_app.domain.ports.model_router import ModelRouter
from new_latex_app.domain.ports.pdf_compiler import PdfCompiler
from new_latex_app.domain.ports.preprocessing import ImagePreprocessor
from new_latex_app.domain.ports.question_segmentation import QuestionSegmenter
from new_latex_app.domain.ports.region_classification import RegionClassifier
from new_latex_app.domain.ports.rule_engine import RuleEngine
from new_latex_app.domain.ports.structure_analyzer import DocumentStructureAnalyzer
from new_latex_app.domain.ports.validation import ValidationEngine

logger: logging.Logger = logging.getLogger(__name__)

ResultT = TypeVar("ResultT")


@dataclass(frozen=True, slots=True)
class DocumentPipeline:
    """Coordinates the full document-to-LaTeX pipeline through domain ports."""

    document_loader: DocumentLoader
    image_preprocessor: ImagePreprocessor
    layout_detector: LayoutDetector
    question_segmenter: QuestionSegmenter
    region_classifier: RegionClassifier
    model_router: ModelRouter
    structure_analyzer: DocumentStructureAnalyzer
    rule_engine: RuleEngine
    chemistry_processor: ChemistryProcessor
    latex_builder: LatexBuilder
    validation_engine: ValidationEngine
    export_manager: ExportManager
    pdf_compiler: PdfCompiler

    def run(self, document: InputDocument, workspace_path: Path, session_id: UUID) -> ProcessingResult:
        """Run all pipeline stages using only temporary workspace paths."""
        started_at = time.perf_counter()
        logger.info("Pipeline started")
        try:
            pages = self._timed(PipelineStageName.DOCUMENT_LOADER, self.document_loader.load, document, workspace_path)
            pages = self._timed(PipelineStageName.IMAGE_PREPROCESSING, self.image_preprocessor.preprocess, pages, workspace_path)
            regions = self._timed(PipelineStageName.LAYOUT_DETECTION, self.layout_detector.detect, pages)
            regions = self._timed(PipelineStageName.QUESTION_SEGMENTATION, self.question_segmenter.segment, regions)
            regions = self._timed(PipelineStageName.REGION_CLASSIFICATION, self.region_classifier.classify, pages, regions)
            contents = self._timed(PipelineStageName.MODEL_ROUTER, self.model_router.recognize, pages, regions, workspace_path)
            structure = self._timed(PipelineStageName.DOCUMENT_STRUCTURE_ANALYZER, self.structure_analyzer.analyze, pages, contents)
            structure = self._timed(PipelineStageName.RULE_ENGINE, self.rule_engine.apply, structure)
            structure = self._timed(PipelineStageName.CHEMISTRY_PROCESSOR, self.chemistry_processor.process, structure)
            latex_document = self._timed(PipelineStageName.LATEX_BUILDER, self.latex_builder.build, structure, workspace_path)
            latex_document = self._timed(PipelineStageName.VALIDATION_ENGINE, self.validation_engine.validate, latex_document)
            export_root = self._timed(
                PipelineStageName.EXPORT_MANAGER,
                self.export_manager.export,
                latex_document,
                tuple(
                    content.metadata
                    for content in structure.contents
                    if content.metadata.get("asset_filename") and content.metadata.get("asset_relpath")
                ),
                workspace_path,
            )
            compiled_pdf = self._timed(PipelineStageName.PDF_COMPILER, self.pdf_compiler.compile, latex_document, workspace_path)
            if latex_document.output_path is None:
                msg = "LaTeX builder did not provide an output path"
                raise ValueError(msg)
            logger.info("Pipeline completed in %.3fs", time.perf_counter() - started_at)
            return ProcessingResult(
                tex_path=latex_document.output_path,
                pdf_path=compiled_pdf.path,
                export_path=export_root,
                session_id=session_id,
            )
        except Exception:
            logger.exception("Pipeline failed")
            raise

    def _timed(
        self,
        stage_name: PipelineStageName,
        operation: Callable[..., ResultT],
        *args: object,
    ) -> ResultT:
        """Run an operation while logging only non-sensitive lifecycle metadata."""
        started_at = time.perf_counter()
        logger.info("Stage started: %s", stage_name.value)
        result = operation(*args)
        logger.info("Stage completed: %s in %.3fs", stage_name.value, time.perf_counter() - started_at)
        return result
