"""Unit tests for SpatialBlockSegmenter."""

import pytest
from new_latex_app.domain.services.spatial_block_segmenter import SpatialBlockSegmenter


def test_segment_lines_empty() -> None:
    segmenter = SpatialBlockSegmenter()
    assert segmenter.segment_lines([]) == []
    assert segmenter.segment_lines([{"words": []}]) == [{"words": []}]


def test_segment_lines_single_word() -> None:
    segmenter = SpatialBlockSegmenter()
    reconstructed_lines = [
        {
            "text": "Hello",
            "bbox": [[10.0, 10.0], [50.0, 10.0], [50.0, 30.0], [10.0, 30.0]],
            "words": [
                {
                    "text": "Hello",
                    "bbox": [[10.0, 10.0], [50.0, 10.0], [50.0, 30.0], [10.0, 30.0]],
                }
            ],
        }
    ]
    blocks = segmenter.segment_lines(reconstructed_lines)
    assert len(blocks) == 1
    assert blocks[0]["text"] == "Hello"
    assert blocks[0]["bbox"] == [[10.0, 10.0], [50.0, 10.0], [50.0, 30.0], [10.0, 30.0]]
    assert len(blocks[0]["words"]) == 1
    assert blocks[0]["words"][0]["text"] == "Hello"


def test_segment_lines_uniform_sentence_no_split() -> None:
    # A standard line of text where gaps are uniform and smaller than normal threshold.
    # Height of words = 20.0
    # Gaps:
    # "The" (10 to 40) -> Gap 10 -> "quick" (50 to 100) -> Gap 10 -> "brown" (110 to 160) -> Gap 10 -> "fox" (170 to 200)
    # Gaps are all 10. Median gap = 10. Median height = 20.
    # Adaptive threshold: max(3.0 * 10, 1.5 * 20) = max(30, 30) = 30.
    # Since all gaps (10) are <= 30, no split should occur.
    segmenter = SpatialBlockSegmenter()
    reconstructed_lines = [
        {
            "words": [
                {"text": "The", "bbox": [[10.0, 10.0], [40.0, 10.0], [40.0, 30.0], [10.0, 30.0]]},
                {"text": "quick", "bbox": [[50.0, 10.0], [100.0, 10.0], [100.0, 30.0], [50.0, 30.0]]},
                {"text": "brown", "bbox": [[110.0, 10.0], [160.0, 10.0], [160.0, 30.0], [110.0, 30.0]]},
                {"text": "fox", "bbox": [[170.0, 10.0], [200.0, 10.0], [200.0, 30.0], [170.0, 30.0]]},
            ]
        }
    ]
    
    blocks = segmenter.segment_lines(reconstructed_lines)
    assert len(blocks) == 1
    assert blocks[0]["text"] == "The quick brown fox"
    assert len(blocks[0]["words"]) == 4


def test_segment_lines_mcq_options_split() -> None:
    # 4 MCQ options on the same line with large gaps between them.
    # Heights = 20.0. Median height = 20.
    # Gaps:
    # (A) -> Option -> 1 (gaps = 10, 10)
    # 1 -> (B) (gap = 140)
    # (B) -> Option -> 2 (gaps = 10, 10)
    # 2 -> (C) (gap = 140)
    # (C) -> Option -> 3 (gaps = 10, 10)
    # 3 -> (D) (gap = 140)
    # (D) -> Option -> 4 (gaps = 10, 10)
    # Gaps list: [10, 10, 140, 10, 10, 140, 10, 10, 140, 10, 10]
    # Median gap: 10
    # Threshold: max(3.0 * 10, 1.5 * 20) = 30.
    # The 140 gaps are > 30, so they split.
    segmenter = SpatialBlockSegmenter()
    reconstructed_lines = [
        {
            "words": [
                {"text": "(A)", "bbox": [[0.0, 10.0], [30.0, 10.0], [30.0, 30.0], [0.0, 30.0]]},
                {"text": "Option", "bbox": [[40.0, 10.0], [90.0, 10.0], [90.0, 30.0], [40.0, 30.0]]},
                {"text": "1", "bbox": [[100.0, 10.0], [110.0, 10.0], [110.0, 30.0], [100.0, 30.0]]},
                
                {"text": "(B)", "bbox": [[250.0, 10.0], [280.0, 10.0], [280.0, 30.0], [250.0, 30.0]]},
                {"text": "Option", "bbox": [[290.0, 10.0], [340.0, 10.0], [340.0, 30.0], [290.0, 30.0]]},
                {"text": "2", "bbox": [[350.0, 10.0], [360.0, 10.0], [360.0, 30.0], [350.0, 30.0]]},
                
                {"text": "(C)", "bbox": [[500.0, 10.0], [530.0, 10.0], [530.0, 30.0], [500.0, 30.0]]},
                {"text": "Option", "bbox": [[540.0, 10.0], [590.0, 10.0], [590.0, 30.0], [540.0, 30.0]]},
                {"text": "3", "bbox": [[600.0, 10.0], [610.0, 10.0], [610.0, 30.0], [600.0, 30.0]]},
                
                {"text": "(D)", "bbox": [[750.0, 10.0], [780.0, 10.0], [780.0, 30.0], [750.0, 30.0]]},
                {"text": "Option", "bbox": [[790.0, 10.0], [840.0, 10.0], [840.0, 30.0], [790.0, 30.0]]},
                {"text": "4", "bbox": [[850.0, 10.0], [860.0, 10.0], [860.0, 30.0], [850.0, 30.0]]},
            ]
        }
    ]

    blocks = segmenter.segment_lines(reconstructed_lines)
    assert len(blocks) == 4
    
    assert blocks[0]["text"] == "(A) Option 1"
    assert blocks[0]["bbox"] == [[0.0, 10.0], [110.0, 10.0], [110.0, 30.0], [0.0, 30.0]]
    assert len(blocks[0]["words"]) == 3
    
    assert blocks[1]["text"] == "(B) Option 2"
    assert blocks[1]["bbox"] == [[250.0, 10.0], [360.0, 10.0], [360.0, 30.0], [250.0, 30.0]]
    assert len(blocks[1]["words"]) == 3
    
    assert blocks[2]["text"] == "(C) Option 3"
    assert blocks[2]["bbox"] == [[500.0, 10.0], [610.0, 10.0], [610.0, 30.0], [500.0, 30.0]]
    assert len(blocks[2]["words"]) == 3
    
    assert blocks[3]["text"] == "(D) Option 4"
    assert blocks[3]["bbox"] == [[750.0, 10.0], [860.0, 10.0], [860.0, 30.0], [750.0, 30.0]]
    assert len(blocks[3]["words"]) == 3


def test_segment_lines_different_bbox_formats() -> None:
    # A dummy object to represent attributes-based bbox.
    class DummyBbox:
        def __init__(self, x: float, y: float, w: float, h: float) -> None:
            self.x = x
            self.y = y
            self.width = w
            self.height = h

    segmenter = SpatialBlockSegmenter()
    reconstructed_lines = [
        {
            "words": [
                # Format 1: Object attributes
                {"text": "Obj", "bbox": DummyBbox(10.0, 10.0, 30.0, 20.0)},
                # Format 3: Flat list [x, y, w, h]
                {"text": "Flat", "bbox": [50.0, 10.0, 40.0, 20.0]},
                # Format 4: Dictionary
                {"text": "Dict", "bbox": {"x": 100.0, "y": 10.0, "width": 50.0, "height": 20.0}},
            ]
        }
    ]

    blocks = segmenter.segment_lines(reconstructed_lines)
    assert len(blocks) == 1
    assert blocks[0]["text"] == "Obj Flat Dict"
    # Overlapping or normal gaps, so no split:
    # Obj: 10 to 40
    # Flat: 50 to 90 (gap = 10)
    # Dict: 100 to 150 (gap = 10)
    # Enclosing bbox: xmin=10, ymin=10, xmax=150, ymax=30
    assert blocks[0]["bbox"] == [[10.0, 10.0], [150.0, 10.0], [150.0, 30.0], [10.0, 30.0]]
