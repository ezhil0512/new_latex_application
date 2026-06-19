"""Region classification interface."""

from typing import Protocol
import logging

from new_latex_app.domain.entities import DocumentRegion, PageImage

logger: logging.Logger = logging.getLogger(__name__)


class RegionClassifier(Protocol):
    """Classify semantic types for detected regions."""

    def classify(
        self,
        pages: tuple[PageImage, ...],
        regions: tuple[DocumentRegion, ...],
    ) -> tuple[DocumentRegion, ...]:
        """Return semantically classified regions."""
        ...
