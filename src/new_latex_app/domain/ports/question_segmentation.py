"""Question segmentation interface."""

from typing import Protocol
import logging

from new_latex_app.domain.entities import DocumentRegion

logger: logging.Logger = logging.getLogger(__name__)


class QuestionSegmenter(Protocol):
    """Group detected regions into questions and options."""

    def segment(self, regions: tuple[DocumentRegion, ...]) -> tuple[DocumentRegion, ...]:
        """Return question-aware regions."""
        ...
