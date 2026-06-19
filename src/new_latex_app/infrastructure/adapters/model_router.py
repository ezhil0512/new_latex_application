"""Composite model router for independent offline recognizers."""

from pathlib import Path
from typing import Protocol
import logging

from new_latex_app.domain.entities import DocumentRegion, PageImage, RecognizedContent

logger: logging.Logger = logging.getLogger(__name__)


class _Recognizer(Protocol):
    """A recognizer compatible with the model-router stage."""

    def recognize(
        self,
        pages: tuple[PageImage, ...],
        regions: tuple[DocumentRegion, ...],
        workspace_path: Path,
    ) -> tuple[RecognizedContent, ...]:
        """Return recognized content for the regions the recognizer owns."""
        ...


class CompositeModelRouter:
    """Route layout regions to independent recognizers without sharing internals."""

    def __init__(self, recognizers: tuple[_Recognizer, ...]) -> None:
        """Create a composite router from stage-specific recognizers."""
        self._recognizers = recognizers

    def recognize(
        self,
        pages: tuple[PageImage, ...],
        regions: tuple[DocumentRegion, ...],
        workspace_path: Path,
    ) -> tuple[RecognizedContent, ...]:
        """Return separate recognized-content objects from each recognizer."""
        logger.info("Composite model routing started")
        contents: list[RecognizedContent] = []
        for recognizer in self._recognizers:
            contents.extend(recognizer.recognize(pages, regions, workspace_path))
        logger.info("Composite model routing completed")
        return tuple(contents)
