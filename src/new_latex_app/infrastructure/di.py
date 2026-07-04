"""Dependency injection container for application assembly."""

from dataclasses import dataclass
import logging
import threading

from new_latex_app.application.pipeline import DocumentPipeline
from new_latex_app.application.services import DocumentProcessingService
from new_latex_app.infrastructure.adapters.pdf_compiler import PassThroughPdfCompiler
from new_latex_app.infrastructure.adapters.validation_engine import PassThroughValidationEngine
from new_latex_app.infrastructure.adapters.region_classifier import VisualRegionClassifier
from new_latex_app.infrastructure.adapters.document_loader import PyMuPdfDocumentLoader
from new_latex_app.infrastructure.adapters.image_preprocessor import OpenCvImagePreprocessor
from new_latex_app.infrastructure.adapters.layout_detector import OpenCvLayoutDetector
from new_latex_app.infrastructure.adapters.diagram_processor import DiagramAssetProcessor
from new_latex_app.infrastructure.adapters.model_router import CompositeModelRouter
from new_latex_app.infrastructure.adapters.paddle_ocr import PaddleOcrTextRecognizer
from new_latex_app.infrastructure.adapters.pix2text_math_ocr import Pix2TextMathOcrRecognizer
from new_latex_app.infrastructure.adapters.question_segmenter import VisualQuestionSegmenter
from new_latex_app.infrastructure.adapters.rule_engine import MetadataRuleEngine
from new_latex_app.infrastructure.adapters.chemistry_processor import MetadataChemistryProcessor
from new_latex_app.infrastructure.adapters.export_manager import TemporaryExportManager
from new_latex_app.infrastructure.adapters.latex_builder import DefaultLatexBuilder
from new_latex_app.infrastructure.adapters.structure_analyzer import MetadataDocumentStructureAnalyzer
from new_latex_app.infrastructure.config import AppSettings, SettingsLoader
from new_latex_app.infrastructure.file_staging import LocalInputStager
from new_latex_app.infrastructure.logging_config import LoggingConfigurator
from new_latex_app.infrastructure.workspace import TemporaryWorkspaceManager

logger: logging.Logger = logging.getLogger(__name__)


_paddle_ocr_recognizer: PaddleOcrTextRecognizer | None = None
_pix2text_recognizer: Pix2TextMathOcrRecognizer | None = None
_recognizer_lock = threading.Lock()


@dataclass(frozen=True, slots=True)
class Container:
    """Small explicit dependency injection container."""

    settings: AppSettings

    @classmethod
    def bootstrap(cls) -> "Container":
        """Build a container from runtime configuration."""
        settings = SettingsLoader().load()
        LoggingConfigurator(settings.config_dir).configure()
        logger.info("Dependency container bootstrapped")
        return cls(settings=settings)

    def workspace_manager(self) -> TemporaryWorkspaceManager:
        """Create a temporary workspace manager."""
        return TemporaryWorkspaceManager(temp_root=self.settings.temp_root)

    def input_stager(self) -> LocalInputStager:
        """Create an input stager for temporary upload handling."""
        return LocalInputStager()

    def document_pipeline(self) -> DocumentPipeline:
        """Create the document pipeline with replaceable adapters."""
        logger.info("Document pipeline assembly started")
        global _paddle_ocr_recognizer, _pix2text_recognizer
        with _recognizer_lock:
            if _paddle_ocr_recognizer is None:
                _paddle_ocr_recognizer = PaddleOcrTextRecognizer()
            if _pix2text_recognizer is None:
                _pix2text_recognizer = Pix2TextMathOcrRecognizer()

        return DocumentPipeline(
            document_loader=PyMuPdfDocumentLoader(),
            image_preprocessor=OpenCvImagePreprocessor(),
            layout_detector=OpenCvLayoutDetector(),
            question_segmenter=VisualQuestionSegmenter(),
            region_classifier=VisualRegionClassifier(),
            model_router=CompositeModelRouter(
                recognizers=(
                    DiagramAssetProcessor(),
                    _paddle_ocr_recognizer,
                    _pix2text_recognizer,
                )
            ),
            structure_analyzer=MetadataDocumentStructureAnalyzer(),
            rule_engine=MetadataRuleEngine(),
            chemistry_processor=self.chemistry_processor(),
            latex_builder=DefaultLatexBuilder(),
            validation_engine=PassThroughValidationEngine(),
            export_manager=self.export_manager(),
            pdf_compiler=PassThroughPdfCompiler(),
        )

    def chemistry_processor(self) -> MetadataChemistryProcessor:
        """Create a chemistry processor adapter for chemistry content normalization."""
        return MetadataChemistryProcessor()

    def export_manager(self) -> TemporaryExportManager:
        """Create an export manager adapter for packaging LaTeX and assets."""
        return TemporaryExportManager()

    def document_processing_service(self) -> DocumentProcessingService:
        """Create the document processing use case service."""
        logger.info("Document processing service assembly started")
        return DocumentProcessingService(
            pipeline=self.document_pipeline(),
            workspace_manager=self.workspace_manager(),
            input_stager=self.input_stager(),
        )
