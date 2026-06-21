from pathlib import Path
from typing import Protocol
import logging

from new_latex_app.domain.entities import LatexDocument

logger: logging.Logger = logging.getLogger(__name__)


class ExportManager(Protocol):
    """Package LaTeX source and diagram assets into a temporary export directory."""

    def export(
        self,
        latex_document: LatexDocument,
        asset_metadata: tuple[dict[str, str], ...],
        workspace_path: Path,
    ) -> Path:
        """Create a temporary export package and return its root path."""
        ...
