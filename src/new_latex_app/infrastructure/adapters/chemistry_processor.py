"""Concrete chemistry processor adapter for text normalization."""

import logging
import re
import time
from typing import Any

from new_latex_app.domain.entities import DocumentStructure, RecognizedContent
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError
from new_latex_app.domain.ports.chemistry_processor import ChemistryProcessor

logger: logging.Logger = logging.getLogger(__name__)


class MetadataChemistryProcessor:
    """Normalize chemistry-specific text and annotate chemistry metadata."""

    _CHEMISTRY_PATTERN = re.compile(
        r"\b(?:[A-Z][a-z]?\d|[A-Z][a-z]?\(|\d+[+-]|\([aqs lg]+\)|->|=>|⇌|<=>|<->|→|←|↔)"
    )
    _ARROW_PATTERN = re.compile(r"<=>|<->|->|=>|→|←|⇌|↔")
    _STATE_PATTERN = re.compile(r"\((aq|s|l|g)\)", re.IGNORECASE)
    _IONIC_CHARGE_PATTERN = re.compile(r"(?<![\^_])\b([A-Za-z][A-Za-z0-9()]*?)(\d*[+-])\b")
    _SUBSCRIPT_PATTERN = re.compile(r"(?<![\\_^])([A-Za-z)])(\d+)")
    _SUPERSCRIPT_PATTERN = re.compile(r"\^(\d*[+-]|[+-])")

    _ARROW_REPLACEMENTS = {
        "<=>": r"\\rightleftharpoons",
        "<->": r"\\rightleftharpoons",
        "->": r"\\rightarrow",
        "=>": r"\\rightarrow",
        "→": r"\\rightarrow",
        "←": r"\\leftarrow",
        "⇌": r"\\rightleftharpoons",
        "↔": r"\\rightleftharpoons",
    }

    def process(self, structure: DocumentStructure) -> DocumentStructure:
        """Return the document structure with chemistry metadata annotations."""
        started_at = time.perf_counter()
        logger.info("Chemistry processor started")

        self._validate_structure(structure)
        contents = tuple(self._process_content(index, content) for index, content in enumerate(structure.contents))
        chemistry_items = tuple(
            {
                "content_index": index,
                "normalized_text": content.metadata["chemistry"]["normalized_text"],
                "patterns": content.metadata["chemistry"]["patterns"],
            }
            for index, content in enumerate(contents)
            if "chemistry" in content.metadata
        )

        metadata = dict(structure.metadata)
        metadata["chemistry_processor"] = "metadata_document_chemistry_processor"
        metadata["chemistry_items"] = chemistry_items

        logger.info("Chemistry processor completed in %.3fs", time.perf_counter() - started_at)
        return DocumentStructure(
            title=structure.title,
            pages=structure.pages,
            regions=structure.regions,
            contents=contents,
            metadata=metadata,
        )

    def _validate_structure(self, structure: DocumentStructure) -> None:
        if not structure.pages or not structure.contents:
            raise PipelineStageError("Cannot process chemistry in an empty document")
        if not isinstance(structure.metadata, dict):
            raise PipelineStageError("Invalid document metadata for chemistry processor")

    def _process_content(self, index: int, content: RecognizedContent) -> RecognizedContent:
        if content.text is None or not self._contains_chemistry(content.text):
            return content

        normalized_text = self._normalize_text(content.text)
        metadata = dict(content.metadata)
        metadata["chemistry"] = {
            "is_chemical": True,
            "normalized_text": normalized_text,
            "patterns": self._detect_patterns(content.text),
        }
        return RecognizedContent(
            region=content.region,
            latex=content.latex,
            text=content.text,
            asset_path=content.asset_path,
            metadata=metadata,
        )

    def _contains_chemistry(self, text: str) -> bool:
        return bool(self._CHEMISTRY_PATTERN.search(text))

    def _normalize_text(self, text: str) -> str:
        normalized = text
        normalized = self._normalize_reaction_arrows(normalized)
        normalized = self._normalize_state_symbols(normalized)
        normalized = self._normalize_ionic_charge(normalized)
        normalized = self._normalize_superscripts(normalized)
        normalized = self._normalize_subscripts(normalized)
        return normalized

    def _normalize_reaction_arrows(self, text: str) -> str:
        def replacement(match: re.Match[str]) -> str:
            return self._ARROW_REPLACEMENTS[match.group(0)]

        return self._ARROW_PATTERN.sub(replacement, text)

    def _normalize_state_symbols(self, text: str) -> str:
        return self._STATE_PATTERN.sub(lambda match: r"\,({})".format(match.group(1).lower()), text)

    def _normalize_ionic_charge(self, text: str) -> str:
        return self._IONIC_CHARGE_PATTERN.sub(lambda match: f"{match.group(1)}^{{{match.group(2)}}}", text)

    def _normalize_superscripts(self, text: str) -> str:
        return self._SUPERSCRIPT_PATTERN.sub(lambda match: f"^{{{match.group(1)}}}", text)

    def _normalize_subscripts(self, text: str) -> str:
        return self._SUBSCRIPT_PATTERN.sub(lambda match: f"{match.group(1)}_{{{match.group(2)}}}", text)

    def _detect_patterns(self, text: str) -> tuple[str, ...]:
        patterns = []
        if self._ARROW_PATTERN.search(text):
            patterns.append("reaction_arrow")
        if self._STATE_PATTERN.search(text):
            patterns.append("state_symbol")
        if self._IONIC_CHARGE_PATTERN.search(text):
            patterns.append("ionic_charge")
        if self._SUBSCRIPT_PATTERN.search(text):
            patterns.append("subscript")
        if self._SUPERSCRIPT_PATTERN.search(text):
            patterns.append("superscript")
        return tuple(sorted(set(patterns)))
