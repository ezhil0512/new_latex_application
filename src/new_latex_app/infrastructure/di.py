"""Dependency injection container for application assembly."""

from dataclasses import dataclass
import logging

from new_latex_app.application.pipeline import DocumentPipeline
from new_latex_app.application.services import DocumentProcessingService
from new_latex_app.infrastructure.adapters.stubs import (
    StubPdfCompiler,
    StubRegionClassifier,
    StubValidationEngine,
)
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
        return DocumentPipeline(
            document_loader=PyMuPdfDocumentLoader(),
            image_preprocessor=OpenCvImagePreprocessor(),
            layout_detector=OpenCvLayoutDetector(),
            question_segmenter=VisualQuestionSegmenter(),
            region_classifier=StubRegionClassifier(),
            model_router=CompositeModelRouter(
                recognizers=(
                    DiagramAssetProcessor(),
                    PaddleOcrTextRecognizer(),
                    Pix2TextMathOcrRecognizer(),
                )
            ),
            structure_analyzer=MetadataDocumentStructureAnalyzer(),
            rule_engine=MetadataRuleEngine(),
            chemistry_processor=self.chemistry_processor(),
            latex_builder=DefaultLatexBuilder(),
            validation_engine=StubValidationEngine(),
            export_manager=self.export_manager(),
            pdf_compiler=StubPdfCompiler(),
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
