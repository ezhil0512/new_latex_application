"""Placeholder adapters used until concrete offline implementations are added."""

from pathlib import Path
from typing import NoReturn
import logging

from new_latex_app.domain.entities import (
    CompiledPdf,
    DocumentRegion,
    DocumentStructure,
    InputDocument,
    LatexDocument,
    PageImage,
    RecognizedContent,
)
from new_latex_app.domain.exceptions import PipelineStageError

logger: logging.Logger = logging.getLogger(__name__)


class NotImplementedAdapter:
    """Base class for foundation-only adapters."""

    stage_name: str = "unknown"

    def _raise(self) -> NoReturn:
        """Raise a consistent not-implemented error without sensitive data."""
        logger.warning("Adapter not implemented: %s", self.stage_name)
        raise PipelineStageError(f"Adapter not implemented: {self.stage_name}")


class StubDocumentLoader(NotImplementedAdapter):
    """Document loader placeholder."""

    stage_name = "document_loader"

    def load(self, document: InputDocument, workspace_path: Path) -> tuple[PageImage, ...]:
        """Reject execution until a real loader is registered."""
        self._raise()


class StubImagePreprocessor(NotImplementedAdapter):
    """Image preprocessing placeholder."""

    stage_name = "image_preprocessing"

    def preprocess(self, pages: tuple[PageImage, ...], workspace_path: Path) -> tuple[PageImage, ...]:
        """Reject execution until a real preprocessor is registered."""
        self._raise()


class StubLayoutDetector(NotImplementedAdapter):
    """Layout detector placeholder."""

    stage_name = "layout_detection"

    def detect(self, pages: tuple[PageImage, ...]) -> tuple[DocumentRegion, ...]:
        """Reject execution until a real detector is registered."""
        self._raise()


class StubQuestionSegmenter(NotImplementedAdapter):
    """Question segmenter placeholder."""

    stage_name = "question_segmentation"

    def segment(self, regions: tuple[DocumentRegion, ...]) -> tuple[DocumentRegion, ...]:
        """Reject execution until a real segmenter is registered."""
        self._raise()


class StubRegionClassifier(NotImplementedAdapter):
    """Region classifier placeholder."""

    stage_name = "region_classification"

    def classify(
        self,
        pages: tuple[PageImage, ...],
        regions: tuple[DocumentRegion, ...],
    ) -> tuple[DocumentRegion, ...]:
        """Reject execution until a real classifier is registered."""
        self._raise()


class StubModelRouter(NotImplementedAdapter):
    """Model router placeholder."""

    stage_name = "model_router"

    def recognize(
        self,
        pages: tuple[PageImage, ...],
        regions: tuple[DocumentRegion, ...],
        workspace_path: Path,
    ) -> tuple[RecognizedContent, ...]:
        """Reject execution until a real router is registered."""
        self._raise()


class StubDocumentStructureAnalyzer(NotImplementedAdapter):
    """Document structure analyzer placeholder."""

    stage_name = "document_structure_analyzer"

    def analyze(
        self,
        pages: tuple[PageImage, ...],
        contents: tuple[RecognizedContent, ...],
    ) -> DocumentStructure:
        """Reject execution until a real analyzer is registered."""
        self._raise()


class StubRuleEngine(NotImplementedAdapter):
    """Rule engine placeholder."""

    stage_name = "rule_engine"

    def apply(self, structure: DocumentStructure) -> DocumentStructure:
        """Reject execution until a real rule engine is registered."""
        self._raise()


class StubLatexBuilder(NotImplementedAdapter):
    """LaTeX builder placeholder."""

    stage_name = "latex_builder"

    def build(self, structure: DocumentStructure, workspace_path: Path) -> LatexDocument:
        """Reject execution until a real builder is registered."""
        self._raise()


class StubValidationEngine(NotImplementedAdapter):
    """Validation engine placeholder."""

    stage_name = "validation_engine"

    def validate(self, latex_document: LatexDocument) -> LatexDocument:
        """Reject execution until a real validator is registered."""
        self._raise()


class StubPdfCompiler(NotImplementedAdapter):
    """PDF compiler placeholder."""

    stage_name = "pdf_compiler"

    def compile(self, latex_document: LatexDocument, workspace_path: Path) -> CompiledPdf:
        """Reject execution until a real compiler is registered."""
        self._raise()
