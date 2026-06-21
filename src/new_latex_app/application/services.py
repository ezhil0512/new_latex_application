"""Application services for document processing use cases."""

from dataclasses import dataclass
import logging
import threading
from pathlib import Path
from uuid import UUID

from new_latex_app.application.dto import ProcessDocumentCommand, ProcessDocumentResponse
from new_latex_app.application.pipeline import DocumentPipeline
from new_latex_app.domain.entities import InputDocument
from new_latex_app.domain.enums import InputFormat
from new_latex_app.domain.exceptions import UnsupportedInputError
from new_latex_app.domain.ports.input_staging import InputStager
from new_latex_app.domain.ports.workspace import WorkspaceManager

logger: logging.Logger = logging.getLogger(__name__)

_session_export_paths: dict[UUID, Path] = {}
_session_export_paths_lock = threading.Lock()


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
            with _session_export_paths_lock:
                _session_export_paths[session.session_id] = result.export_path
            return ProcessDocumentResponse(
                session_id=session.session_id,
                tex_path=result.tex_path,
                pdf_path=result.pdf_path,
                export_path=result.export_path,
            )

    def get_export_path(self, session_id: UUID) -> Path | None:
        """Resolve the export package location for a completed session."""
        with _session_export_paths_lock:
            return _session_export_paths.get(session_id)

    def _detect_format(self, suffix: str) -> InputFormat:
        """Map a file suffix to a supported input format."""
        normalized = suffix.lower().lstrip(".")
        try:
            return InputFormat(normalized)
        except ValueError as error:
            logger.warning("Unsupported input format rejected")
            raise UnsupportedInputError(f"Unsupported input format: {normalized}") from error
