"""Layout detection interface."""

from typing import Protocol
import logging

from new_latex_app.domain.entities import DocumentRegion, PageImage

logger: logging.Logger = logging.getLogger(__name__)


class LayoutDetector(Protocol):
    """Detect coarse page layout regions."""

    def detect(self, pages: tuple[PageImage, ...]) -> tuple[DocumentRegion, ...]:
        """Return detected layout regions."""
        ...
