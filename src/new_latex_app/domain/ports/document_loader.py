"""Document loading interface."""

from pathlib import Path
from typing import Protocol
import logging

from new_latex_app.domain.entities import InputDocument, PageImage

logger: logging.Logger = logging.getLogger(__name__)


class DocumentLoader(Protocol):
    """Load PDF or image input into page images."""

    def load(self, document: InputDocument, workspace_path: Path) -> tuple[PageImage, ...]:
        """Render or normalize an input document into temporary page images."""
        ...
