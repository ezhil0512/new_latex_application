"""Domain enumerations used across the document pipeline."""

from enum import Enum
import logging

logger: logging.Logger = logging.getLogger(__name__)


class InputFormat(str, Enum):
    """Supported uploaded document formats."""

    PDF = "pdf"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    BMP = "bmp"
    TIFF = "tiff"


class RegionType(str, Enum):
    """Semantic region types detected in educational documents."""

    TEXT = "text"
    QUESTION = "question"
    OPTION = "option"
    FORMULA = "formula"
    TABLE = "table"
    FIGURE = "figure"
    GRAPH = "graph"
    PHYSICS_DIAGRAM = "physics_diagram"
    CHEMICAL_STRUCTURE = "chemical_structure"
    BIOLOGY_DIAGRAM = "biology_diagram"
    HEADER = "header"
    FOOTER = "footer"
    UNKNOWN = "unknown"


class PipelineStageName(str, Enum):
    """Canonical names for processing stages."""

    DOCUMENT_LOADER = "document_loader"
    IMAGE_PREPROCESSING = "image_preprocessing"
    LAYOUT_DETECTION = "layout_detection"
    QUESTION_SEGMENTATION = "question_segmentation"
    REGION_CLASSIFICATION = "region_classification"
    MODEL_ROUTER = "model_router"
    DOCUMENT_STRUCTURE_ANALYZER = "document_structure_analyzer"
    RULE_ENGINE = "rule_engine"
    LATEX_BUILDER = "latex_builder"
    VALIDATION_ENGINE = "validation_engine"
    PDF_COMPILER = "pdf_compiler"
