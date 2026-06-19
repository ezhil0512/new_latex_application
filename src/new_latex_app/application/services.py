"""Application services for document processing use cases."""

from dataclasses import dataclass
import logging

from new_latex_app.application.dto import ProcessDocumentCommand, ProcessDocumentResponse
from new_latex_app.application.pipeline import DocumentPipeline
from new_latex_app.domain.entities import InputDocument
from new_latex_app.domain.enums import InputFormat
from new_latex_app.domain.exceptions import UnsupportedInputError
from new_latex_app.domain.ports.input_staging import InputStager
from new_latex_app.domain.ports.workspace import WorkspaceManager

logger: logging.Logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DocumentProcessingService:
    """Use case service for converting a document into temporary LaTeX/PDF output."""

    pipeline: DocumentPipeline
    workspace_manager: WorkspaceManager
    input_stager: InputStager

    def process(self, command: ProcessDocumentCommand) -> ProcessDocumentResponse:
        """Process a document inside a UUID temporary workspace."""
        input_format = self._detect_format(command.input_path.suffix)
        logger.info("Document processing request accepted")
        with self.workspace_manager.create() as session:
            staged_path = self.input_stager.stage(command.input_path, session.workspace_path)
            document = InputDocument(
                path=staged_path,
                input_format=input_format,
                original_filename=command.original_filename,
            )
            result = self.pipeline.run(
                document=document,
                workspace_path=session.workspace_path,
                session_id=session.session_id,
            )
            logger.info("Document processing request completed")
            return ProcessDocumentResponse(
                session_id=session.session_id,
                tex_path=result.tex_path,
                pdf_path=result.pdf_path,
            )

    def _detect_format(self, suffix: str) -> InputFormat:
        """Map a file suffix to a supported input format."""
        normalized = suffix.lower().lstrip(".")
        try:
            return InputFormat(normalized)
        except ValueError as error:
            logger.warning("Unsupported input format rejected")
            raise UnsupportedInputError(f"Unsupported input format: {normalized}") from error
