"""Unit tests for the concrete document loader adapter."""

from pathlib import Path
import logging

import fitz
from PIL import Image
import pytest

from new_latex_app.domain.entities import InputDocument
from new_latex_app.domain.enums import InputFormat
from new_latex_app.domain.exceptions import UnsupportedInputError
from new_latex_app.infrastructure.adapters.document_loader import PyMuPdfDocumentLoader

logger: logging.Logger = logging.getLogger(__name__)


def test_load_png_normalizes_image_to_workspace(tmp_path: Path) -> None:
    """PNG input should produce one workspace-backed PageImage."""
    source = tmp_path / "source.png"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    Image.new("RGB", (32, 24), color="white").save(source)

    loader = PyMuPdfDocumentLoader()
    pages = loader.load(InputDocument(path=source, input_format=InputFormat.PNG), workspace)

    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert pages[0].width == 32
    assert pages[0].height == 24
    assert pages[0].path.is_file()
    assert workspace in pages[0].path.parents


def test_load_bmp_normalizes_image_to_workspace(tmp_path: Path) -> None:
    """BMP input should be accepted and normalized to a workspace PNG."""
    source = tmp_path / "source.bmp"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    Image.new("RGB", (18, 20), color="white").save(source)

    loader = PyMuPdfDocumentLoader()
    pages = loader.load(InputDocument(path=source, input_format=InputFormat.BMP), workspace)

    assert len(pages) == 1
    assert pages[0].width == 18
    assert pages[0].height == 20
    assert pages[0].path.suffix == ".png"


def test_load_pdf_preserves_page_order(tmp_path: Path) -> None:
    """PDF input should render pages in source order."""
    source = tmp_path / "source.pdf"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    pdf = fitz.open()
    pdf.new_page(width=100, height=120)
    pdf.new_page(width=200, height=220)
    pdf.save(source)
    pdf.close()

    loader = PyMuPdfDocumentLoader(pdf_dpi=72)
    pages = loader.load(InputDocument(path=source, input_format=InputFormat.PDF), workspace)

    assert [page.page_number for page in pages] == [1, 2]
    assert len(pages) == 2
    assert pages[0].path.name < pages[1].path.name
    assert all(page.path.is_file() for page in pages)


def test_load_tiff_preserves_frames(tmp_path: Path) -> None:
    """Multi-frame TIFF input should produce one PageImage per frame."""
    source = tmp_path / "source.tiff"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    first = Image.new("RGB", (10, 12), color="white")
    second = Image.new("RGB", (14, 16), color="black")
    first.save(source, save_all=True, append_images=[second])

    loader = PyMuPdfDocumentLoader()
    pages = loader.load(InputDocument(path=source, input_format=InputFormat.TIFF), workspace)

    assert [page.page_number for page in pages] == [1, 2]
    assert [(page.width, page.height) for page in pages] == [(10, 12), (14, 16)]


def test_missing_file_is_rejected(tmp_path: Path) -> None:
    """Missing inputs should fail before any processing."""
    loader = PyMuPdfDocumentLoader()

    with pytest.raises(FileNotFoundError):
        loader.load(InputDocument(path=tmp_path / "missing.png", input_format=InputFormat.PNG), tmp_path)


def test_empty_file_is_rejected(tmp_path: Path) -> None:
    """Empty inputs should be rejected."""
    source = tmp_path / "empty.png"
    source.write_bytes(b"")
    loader = PyMuPdfDocumentLoader()

    with pytest.raises(ValueError, match="empty"):
        loader.load(InputDocument(path=source, input_format=InputFormat.PNG), tmp_path)


def test_corrupted_image_is_rejected(tmp_path: Path) -> None:
    """Corrupted image files should be rejected."""
    source = tmp_path / "corrupted.png"
    source.write_bytes(b"not a real image")
    loader = PyMuPdfDocumentLoader()

    with pytest.raises(ValueError, match="corrupted|unreadable"):
        loader.load(InputDocument(path=source, input_format=InputFormat.PNG), tmp_path)


def test_corrupted_pdf_is_rejected(tmp_path: Path) -> None:
    """Corrupted PDF files should be rejected."""
    source = tmp_path / "corrupted.pdf"
    source.write_bytes(b"not a real pdf")
    loader = PyMuPdfDocumentLoader()

    with pytest.raises(ValueError, match="corrupted|unreadable"):
        loader.load(InputDocument(path=source, input_format=InputFormat.PDF), tmp_path)


def test_unsupported_extension_is_rejected(tmp_path: Path) -> None:
    """Unsupported extensions should be rejected."""
    source = tmp_path / "source.txt"
    source.write_text("not supported", encoding="utf-8")
    loader = PyMuPdfDocumentLoader()

    with pytest.raises(UnsupportedInputError):
        loader.load(InputDocument(path=source, input_format=InputFormat.PNG), tmp_path)
