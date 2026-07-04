"""Concrete region classifier that preserves layout-detector classifications."""

import logging
import time

from new_latex_app.domain.entities import DocumentRegion, PageImage

logger: logging.Logger = logging.getLogger(__name__)


class VisualRegionClassifier:
    """Accept pre-classified regions from the layout detector as-is.

    The ``OpenCvLayoutDetector`` already assigns ``RegionType``, confidence
    scores, and visual-feature metadata to every region it emits.  This
    adapter satisfies the ``RegionClassifier`` port by forwarding those
    classifications unchanged, keeping the pipeline stage contract intact
    without duplicating work.
    """

    def classify(
        self,
        pages: tuple[PageImage, ...],
        regions: tuple[DocumentRegion, ...],
    ) -> tuple[DocumentRegion, ...]:
        """Return regions with their existing classifications intact."""
        started_at = time.perf_counter()
        logger.info("Region classification started")
        logger.info(
            "Region classification completed in %.3fs (%d regions)",
            time.perf_counter() - started_at,
            len(regions),
        )
        return regions
