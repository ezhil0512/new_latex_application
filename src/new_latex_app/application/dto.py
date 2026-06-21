"""Application request and response dataclasses."""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID
import logging

logger: logging.Logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProcessDocumentCommand:
    """Input command for a document processing request."""

    input_path: Path
    original_filename: str | None = None


@dataclass(frozen=True, slots=True)
class ProcessDocumentResponse:
    """Output metadata for a completed document processing request."""

    session_id: UUID
    tex_path: Path
    pdf_path: Path
    export_path: Path
