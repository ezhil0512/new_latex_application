"""Concrete offline document loader for PDFs and image files."""

from pathlib import Path
import logging
import time

import fitz
from PIL import Image, ImageSequence, UnidentifiedImageError

from new_latex_app.domain.entities import InputDocument, PageImage
from new_latex_app.domain.enums import InputFormat
from new_latex_app.domain.exceptions import UnsupportedInputError

logger: logging.Logger = logging.getLogger(__name__)


class PyMuPdfDocumentLoader:
    """Load PDFs with PyMuPDF and image files with Pillow into workspace images."""

    _IMAGE_FORMATS: frozenset[InputFormat] = frozenset(
        {
            InputFormat.PNG,
            InputFormat.JPG,
            InputFormat.JPEG,
            InputFormat.BMP,
            InputFormat.TIFF,
        }
    )
    _EXTENSION_FORMATS: dict[str, InputFormat] = {
        ".pdf": InputFormat.PDF,
        ".png": InputFormat.PNG,
        ".jpg": InputFormat.JPG,
        ".jpeg": InputFormat.JPEG,
        ".bmp": InputFormat.BMP,
        ".tif": InputFormat.TIFF,
        ".tiff": InputFormat.TIFF,
    }

    def __init__(self, pdf_dpi: int = 200) -> None:
        """Create a document loader with a PDF render DPI."""
        if pdf_dpi <= 0:
            raise ValueError("PDF render DPI must be positive")
        self._pdf_dpi = pdf_dpi

    def load(self, document: InputDocument, workspace_path: Path) -> tuple[PageImage, ...]:
        """Render or normalize an input document into temporary page images."""
        started_at = time.perf_counter()
        logger.info("Document loading started")
        self._validate_workspace(workspace_path)
        self._validate_document(document)

        if document.input_format is InputFormat.PDF:
            pages = self._load_pdf(document.path, workspace_path)
        elif document.input_format in self._IMAGE_FORMATS:
            pages = self._load_image(document.path, workspace_path)
        else:
            logger.warning("Unsupported document format rejected")
            raise UnsupportedInputError("Unsupported input format")

        logger.info("Document loading completed in %.3fs", time.perf_counter() - started_at)
        return pages

    def _validate_workspace(self, workspace_path: Path) -> None:
        """Validate that temporary output can be written to the workspace."""
        if not workspace_path.exists() or not workspace_path.is_dir():
            raise FileNotFoundError("Workspace path does not exist")

    def _validate_document(self, document: InputDocument) -> None:
        """Validate file existence, size, and supported extension."""
        if not document.path.exists() or not document.path.is_file():
            raise FileNotFoundError("Input document not found")
        if document.path.stat().st_size == 0:
            raise ValueError("Input document is empty")

        expected_format = self._EXTENSION_FORMATS.get(document.path.suffix.lower())
        if expected_format is None:
            logger.warning("Unsupported file extension rejected")
            raise UnsupportedInputError("Unsupported file extension")
        if expected_format is not document.input_format:
            logger.warning("Input extension and declared format do not match")
            raise UnsupportedInputError("Input extension and declared format do not match")

    def _load_pdf(self, input_path: Path, workspace_path: Path) -> tuple[PageImage, ...]:
        """Render PDF pages to PNG files in their original order."""
        output_dir = self._prepare_output_dir(workspace_path)
        try:
            with fitz.open(input_path) as pdf_document:
                if pdf_document.page_count == 0:
                    raise ValueError("PDF does not contain pages")
                pages: list[PageImage] = []
                for page_index in range(pdf_document.page_count):
                    page = pdf_document.load_page(page_index)
                    pixmap = page.get_pixmap(dpi=self._pdf_dpi, alpha=False)
                    output_path = output_dir / f"page_{page_index + 1:04d}.png"
                    pixmap.save(output_path)
                    pages.append(
                        PageImage(
                            page_number=page_index + 1,
                            path=output_path,
                            width=pixmap.width,
                            height=pixmap.height,
                            dpi=self._pdf_dpi,
                        )
                    )
                return tuple(pages)
        except fitz.FileDataError as error:
            logger.warning("Corrupted PDF rejected")
            raise ValueError("PDF file is corrupted or unreadable") from error

    def _load_image(self, input_path: Path, workspace_path: Path) -> tuple[PageImage, ...]:
        """Validate and normalize image files to PNG files in the workspace."""
        output_dir = self._prepare_output_dir(workspace_path)
        try:
            with Image.open(input_path) as image:
                pages: list[PageImage] = []
                for index, frame in enumerate(ImageSequence.Iterator(image), start=1):
                    normalized = frame.convert("RGB")
                    output_path = output_dir / f"page_{index:04d}.png"
                    normalized.save(output_path, format="PNG")
                    pages.append(
                        PageImage(
                            page_number=index,
                            path=output_path,
                            width=normalized.width,
                            height=normalized.height,
                            dpi=self._read_dpi(frame),
                        )
                    )
                if not pages:
                    raise ValueError("Image does not contain pages")
                return tuple(pages)
        except (UnidentifiedImageError, OSError) as error:
            logger.warning("Corrupted image rejected")
            raise ValueError("Image file is corrupted or unreadable") from error

    def _prepare_output_dir(self, workspace_path: Path) -> Path:
        """Create a temporary page-image output directory under the workspace."""
        output_dir = workspace_path / "document_loader"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _read_dpi(self, image: Image.Image) -> int | None:
        """Read image DPI when available."""
        dpi = image.info.get("dpi")
        if isinstance(dpi, tuple) and dpi:
            return int(round(float(dpi[0])))
        if isinstance(dpi, (int, float)):
            return int(round(float(dpi)))
        return None
