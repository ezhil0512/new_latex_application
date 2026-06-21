"""Dataclasses representing documents, regions, and pipeline outputs."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID
import logging

from new_latex_app.domain.enums import InputFormat, RegionType

logger: logging.Logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """A rectangular area in page coordinates."""

    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class DocumentSession:
    """A UUID-scoped processing session backed by temporary storage."""

    session_id: UUID
    workspace_path: Path


@dataclass(frozen=True, slots=True)
class InputDocument:
    """Metadata for an uploaded document stored only in temporary workspace."""

    path: Path
    input_format: InputFormat
    original_filename: str | None = None


@dataclass(frozen=True, slots=True)
class PageImage:
    """A rendered or uploaded page image in temporary workspace."""

    page_number: int
    path: Path
    width: int
    height: int
    dpi: int | None = None


@dataclass(frozen=True, slots=True)
class DocumentRegion:
    """A classified document region with optional non-sensitive metadata."""

    page_number: int
    region_type: RegionType
    bbox: BoundingBox
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RecognizedContent:
    """Structured content returned by OCR/model adapters without persistence."""

    region: DocumentRegion
    latex: str | None = None
    text: str | None = None
    asset_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DocumentStructure:
    """Hierarchical representation consumed by the LaTeX builder."""

    title: str | None
    pages: tuple[PageImage, ...]
    regions: tuple[DocumentRegion, ...]
    contents: tuple[RecognizedContent, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LatexDocument:
    """In-memory LaTeX artifact and temporary output path."""

    source: str
    output_path: Path | None = None


@dataclass(frozen=True, slots=True)
class CompiledPdf:
    """Temporary compiled PDF artifact."""

    path: Path
    engine: str


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    """Final output metadata for a completed processing session."""

    tex_path: Path
    pdf_path: Path
    export_path: Path
    session_id: UUID
