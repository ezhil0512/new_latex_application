"""Domain service for geometric document block segmentation."""

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class SpatialBlockSegmenter:
    """Segments reconstructed text lines into geometric spatial blocks.

    This component relies purely on horizontal geometry (bounding boxes)
    and does not use regular expressions, machine learning, or text patterns.
    """

    def __init__(
        self,
        gap_multiplier: float = 3.0,
        height_multiplier: float = 1.5,
    ) -> None:
        """Initialize the segmenter.

        Args:
            gap_multiplier: Multiplier applied to the median gap to define the split threshold.
            height_multiplier: Multiplier applied to the median word height to define the baseline threshold floor.
        """
        self.gap_multiplier = gap_multiplier
        self.height_multiplier = height_multiplier

    def segment_lines(self, reconstructed_lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Segments reconstructed lines into spatial blocks based on horizontal gaps.

        Args:
            reconstructed_lines: A list of reconstructed line dicts, where each dict has:
                - "text": The full text of the line (optional/recomputed)
                - "bbox": Bounding box coordinates (optional/recomputed)
                - "words": A list of raw word dictionaries, each containing "text" and "bbox".

        Returns:
            A list of SpatialBlock dicts:
                - "text": The re-joined text of the block.
                - "bbox": Enclosing bounding box of the block.
                - "words": The original raw word dictionaries belonging to the block.
        """
        if not reconstructed_lines:
            return []

        # Step 1: Extract geometries for all words and compile list of word heights and gaps.
        all_word_heights: List[float] = []
        all_gaps: List[float] = []
        
        # We will keep a structured representation of the lines to avoid parsing geometry twice
        processed_lines: List[List[Tuple[Dict[str, Any], float, float, float, float, float]]] = []

        for line_dict in reconstructed_lines:
            words = line_dict.get("words", [])
            if not words:
                continue

            line_processed_words = []
            for w in words:
                geom = self._extract_word_geometry(w)
                if geom is None:
                    continue
                xmin, xmax, ymin, ymax, h = geom
                all_word_heights.append(h)
                line_processed_words.append((w, xmin, xmax, ymin, ymax, h))

            if not line_processed_words:
                continue

            # Sort words horizontally by X-min coordinate
            line_processed_words.sort(key=lambda item: item[1])
            processed_lines.append(line_processed_words)

            # Compute horizontal gaps on lines with >= 2 words
            if len(line_processed_words) >= 2:
                for i in range(len(line_processed_words) - 1):
                    prev_xmax = line_processed_words[i][2]
                    curr_xmin = line_processed_words[i + 1][1]
                    gap = curr_xmin - prev_xmax
                    all_gaps.append(gap)

        if not all_word_heights:
            # If no words or geometries are valid, return reconstructed lines as-is (defensive fallback)
            return reconstructed_lines

        # Step 2: Compute adaptive threshold
        median_height = self._median(all_word_heights)
        
        trimmed_median_gap = 0.0
        if all_gaps:
            sorted_gaps = sorted(all_gaps)
            k = max(1, int(len(sorted_gaps) * 0.70))
            trimmed_gaps = sorted_gaps[:k]
            trimmed_median_gap = self._median(trimmed_gaps)

        # Split threshold is a gap significantly larger than normal
        # We use a floor of height_multiplier * median_height to avoid splitting on tiny normal word spaces
        adaptive_threshold = max(
            self.gap_multiplier * trimmed_median_gap,
            self.height_multiplier * median_height
        )

        logger.debug(
            "Computed spatial segmentation thresholds: median_height=%.2f, trimmed_median_gap=%.2f, threshold=%.2f",
            median_height,
            trimmed_median_gap,
            adaptive_threshold
        )

        # Step 3: Split lines into spatial blocks
        spatial_blocks: List[Dict[str, Any]] = []

        for line_words in processed_lines:
            if not line_words:
                continue

            if len(line_words) == 1:
                # Exactly one word in the line, no splitting needed
                spatial_blocks.append(self._create_block([line_words[0]]))
                continue

            # Group words based on the adaptive threshold
            current_group = [line_words[0]]
            for i in range(1, len(line_words)):
                prev_xmax = line_words[i - 1][2]
                curr_xmin = line_words[i][1]
                gap = curr_xmin - prev_xmax

                if gap > adaptive_threshold:
                    # Gap is significantly larger than normal: split here
                    spatial_blocks.append(self._create_block(current_group))
                    current_group = [line_words[i]]
                else:
                    current_group.append(line_words[i])

            if current_group:
                spatial_blocks.append(self._create_block(current_group))

        return spatial_blocks

    def _create_block(
        self,
        group: List[Tuple[Dict[str, Any], float, float, float, float, float]]
    ) -> Dict[str, Any]:
        """Create a spatial block dictionary from a group of processed words.

        Preserves all geometry and word metadata.
        """
        block_words = [item[0] for item in group]
        
        # Calculate enclosing bounding box
        xmin = min(item[1] for item in group)
        xmax = max(item[2] for item in group)
        ymin = min(item[3] for item in group)
        ymax = max(item[4] for item in group)

        block_bbox = [
            [xmin, ymin],
            [xmax, ymin],
            [xmax, ymax],
            [xmin, ymax]
        ]

        # Re-join texts from original words (fallback/secondary to geometry)
        block_text = " ".join(w.get("text", "") for w in block_words if w.get("text") is not None)

        return {
            "text": block_text,
            "bbox": block_bbox,
            "words": block_words
        }

    def _extract_word_geometry(self, word: Dict[str, Any]) -> Tuple[float, float, float, float, float] | None:
        """Extract xmin, xmax, ymin, ymax, height from a raw word's bounding box."""
        bbox = word.get("bbox")
        if bbox is None:
            return None

        # Format 1: Object with attributes (x, y, width, height)
        if hasattr(bbox, "x") and hasattr(bbox, "y") and hasattr(bbox, "width") and hasattr(bbox, "height"):
            try:
                xmin = float(bbox.x)
                ymin = float(bbox.y)
                h = float(bbox.height)
                xmax = xmin + float(bbox.width)
                return xmin, xmax, ymin, ymin + h, h
            except (ValueError, TypeError):
                pass

        # Format 2: List/tuple of 4 points: [[x0, y0], [x1, y1], [x2, y2], [x3, y3]]
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            if all(isinstance(p, (list, tuple)) and len(p) >= 2 for p in bbox):
                try:
                    ys = [float(p[1]) for p in bbox]
                    xs = [float(p[0]) for p in bbox]
                    xmin = min(xs)
                    ymin = min(ys)
                    h = max(ys) - min(ys)
                    xmax = max(xs)
                    return xmin, xmax, ymin, ymin + h, h
                except (ValueError, TypeError, IndexError):
                    pass
            # Format 3: Flat list/tuple of 4 floats: [x, y, width, height]
            else:
                try:
                    xmin = float(bbox[0])
                    ymin = float(bbox[1])
                    h = float(bbox[3])
                    xmax = xmin + float(bbox[2])
                    return xmin, xmax, ymin, ymin + h, h
                except (ValueError, TypeError, IndexError):
                    pass

        # Format 4: Dict with coordinates
        if isinstance(bbox, dict) and "x" in bbox and "y" in bbox:
            try:
                xmin = float(bbox["x"])
                ymin = float(bbox["y"])
                h = float(bbox.get("height", 0.0))
                xmax = xmin + float(bbox.get("width", 0.0))
                return xmin, xmax, ymin, ymin + h, h
            except (ValueError, TypeError):
                pass

        return None

    def _median(self, values: List[float]) -> float:
        """Calculate the median of a list of floats."""
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        if n % 2 != 0:
            return sorted_vals[n // 2]
        else:
            return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0
