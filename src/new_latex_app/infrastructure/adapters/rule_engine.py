"""Concrete rule engine adapter for structured document normalization."""

import logging
import time
from typing import Any

from new_latex_app.domain.entities import DocumentRegion, DocumentStructure
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError

logger: logging.Logger = logging.getLogger(__name__)


class MetadataRuleEngine:
    """Normalize structure analyzer output for deterministic LaTeX generation."""

    _FIGURE_REGION_TYPES: frozenset[RegionType] = frozenset(
        {
            RegionType.FIGURE,
            RegionType.GRAPH,
            RegionType.PHYSICS_DIAGRAM,
            RegionType.CHEMICAL_STRUCTURE,
            RegionType.BIOLOGY_DIAGRAM,
        }
    )

    def apply(self, structure: DocumentStructure) -> DocumentStructure:
        """Return a normalized document structure with rich question metadata."""
        started_at = time.perf_counter()
        logger.info("Rule engine started")

        self._validate_structure(structure)
        questions = self._normalize_questions(structure)

        metadata = dict(structure.metadata)
        metadata["rule_engine"] = "metadata_document_rule_engine"
        metadata["questions"] = questions
        metadata["question_count"] = len(questions)

        logger.info("Rule engine completed in %.3fs", time.perf_counter() - started_at)
        return DocumentStructure(
            title=structure.title,
            pages=structure.pages,
            regions=structure.regions,
            contents=structure.contents,
            metadata=metadata,
        )

    def _validate_structure(self, structure: DocumentStructure) -> None:
        """Validate the incoming structure before rule enrichment."""
        if not structure.pages or not structure.contents:
            raise PipelineStageError("Cannot apply rules to an empty document structure")
        if not structure.metadata or "questions" not in structure.metadata:
            raise PipelineStageError("Document structure missing question metadata")
        if not isinstance(structure.metadata["questions"], (tuple, list)):
            raise PipelineStageError("Document structure questions metadata is invalid")
        if not structure.regions:
            raise PipelineStageError("Document structure missing region metadata")

    def _normalize_questions(self, structure: DocumentStructure) -> tuple[dict[str, Any], ...]:
        """Convert raw question metadata into a normalized rule-engine model."""
        raw_questions = tuple(structure.metadata["questions"])
        if not raw_questions:
            raise PipelineStageError("Document structure contains no questions")

        self._validate_question_sequence(raw_questions)

        return tuple(self._normalize_question(question, structure) for question in raw_questions)

    def _validate_question_sequence(self, questions: tuple[dict[str, Any], ...]) -> None:
        """Validate question identifiers and order without mutating the input."""
        seen_ids: set[str] = set()
        previous_key: tuple[int, int] | None = None

        for question in questions:
            if not isinstance(question, dict):
                raise PipelineStageError("Invalid question metadata format")

            question_id = question.get("question_id")
            page_number = question.get("page_number")
            question_index = question.get("question_index")
            content_indices = question.get("content_indices")
            region_indices = question.get("region_indices")

            if not isinstance(question_id, str) or not question_id:
                raise PipelineStageError("Question metadata is missing a valid identifier")
            if question_id in seen_ids:
                raise PipelineStageError("Duplicate question identifier in document structure")
            seen_ids.add(question_id)

            if not isinstance(page_number, int) or page_number <= 0:
                raise PipelineStageError("Question metadata contains an invalid page number")
            if not isinstance(question_index, int) or question_index <= 0:
                raise PipelineStageError("Question metadata contains an invalid question index")
            if not isinstance(content_indices, (tuple, list)) or not content_indices:
                raise PipelineStageError("Question metadata contains invalid content references")
            if not isinstance(region_indices, (tuple, list)) or not region_indices:
                raise PipelineStageError("Question metadata contains invalid region references")

            if previous_key is not None:
                current_key = (page_number, question_index)
                if current_key < previous_key:
                    raise PipelineStageError("Invalid question hierarchy")
            previous_key = (page_number, question_index)

    def _normalize_question(self, question: dict[str, Any], structure: DocumentStructure) -> dict[str, Any]:
        """Create normalized question metadata for LaTeX-ready document structure."""
        ordered_content_indices = tuple(int(index) for index in question["content_indices"])
        region_indices = tuple(int(index) for index in question["region_indices"])
        self._validate_question_indices(ordered_content_indices, region_indices, structure)

        text_content_indices = tuple(
            index
            for index in ordered_content_indices
            if structure.contents[index].region.region_type is RegionType.TEXT
        )
        formula_content_indices = tuple(
            index
            for index in ordered_content_indices
            if structure.contents[index].region.region_type is RegionType.FORMULA
        )
        option_content_indices = tuple(
            index
            for index in ordered_content_indices
            if structure.contents[index].region.region_type is RegionType.OPTION
        )
        figure_region_indices = tuple(
            self._region_index(structure.regions, structure.contents[index].region)
            for index in ordered_content_indices
            if structure.contents[index].region.region_type in self._FIGURE_REGION_TYPES
        )
        table_region_indices = tuple(
            self._region_index(structure.regions, structure.contents[index].region)
            for index in ordered_content_indices
            if structure.contents[index].region.region_type is RegionType.TABLE
        )

        blocks = self._build_question_blocks(ordered_content_indices, structure)
        paragraph_groups = tuple(block["content_indices"] for block in blocks if block["block_type"] == "paragraph")
        option_groups = tuple(block["content_indices"] for block in blocks if block["block_type"] == "option_group")

        return {
            "question_id": question["question_id"],
            "page_number": question["page_number"],
            "question_index": question["question_index"],
            "content_indices": ordered_content_indices,
            "region_indices": region_indices,
            "text_content_indices": text_content_indices,
            "formula_content_indices": formula_content_indices,
            "option_content_indices": option_content_indices,
            "option_groups": option_groups,
            "paragraph_groups": paragraph_groups,
            "figure_region_indices": figure_region_indices,
            "table_region_indices": table_region_indices,
            "blocks": blocks,
        }

    def _validate_question_indices(
        self,
        content_indices: tuple[int, ...],
        region_indices: tuple[int, ...],
        structure: DocumentStructure,
    ) -> None:
        """Validate that question references match the available structure."""
        max_content_index = len(structure.contents) - 1
        max_region_index = len(structure.regions) - 1

        for index in content_indices:
            if not isinstance(index, int) or index < 0 or index > max_content_index:
                raise PipelineStageError("Question metadata references missing content")
        for index in region_indices:
            if not isinstance(index, int) or index < 0 or index > max_region_index:
                raise PipelineStageError("Question metadata references missing region")

    def _build_question_blocks(self, ordered_content_indices: tuple[int, ...], structure: DocumentStructure) -> tuple[dict[str, Any], ...]:
        """Create a logical block sequence for each question in reading order."""
        blocks: list[dict[str, Any]] = []
        active_block: dict[str, Any] | None = None

        for content_index in ordered_content_indices:
            region = structure.contents[content_index].region
            block_type = self._block_type(region)
            region_index = self._region_index(structure.regions, region)

            if block_type == "paragraph":
                if active_block and active_block["block_type"] == "paragraph":
                    active_block["content_indices"] += (content_index,)
                    active_block["region_indices"] += (region_index,)
                else:
                    active_block = {
                        "block_type": "paragraph",
                        "content_indices": (content_index,),
                        "region_indices": (region_index,),
                    }
                    blocks.append(active_block)
                continue

            if block_type == "formula" and active_block and active_block["block_type"] == "paragraph":
                active_block["content_indices"] += (content_index,)
                active_block["region_indices"] += (region_index,)
                continue

            if block_type == "option_group":
                if active_block and active_block["block_type"] == "option_group":
                    active_block["content_indices"] += (content_index,)
                    active_block["region_indices"] += (region_index,)
                else:
                    active_block = {
                        "block_type": "option_group",
                        "content_indices": (content_index,),
                        "region_indices": (region_index,),
                    }
                    blocks.append(active_block)
                continue

            if active_block and active_block["block_type"] in {"paragraph", "option_group"}:
                active_block = None

            blocks.append(
                {
                    "block_type": block_type,
                    "content_indices": (content_index,),
                    "region_indices": (region_index,),
                }
            )
            active_block = blocks[-1]

        return tuple(blocks)

    def _block_type(self, region: DocumentRegion) -> str:
        if region.region_type is RegionType.TEXT:
            return "paragraph"
        if region.region_type is RegionType.FORMULA:
            return "formula"
        if region.region_type is RegionType.OPTION:
            return "option_group"
        if region.region_type in self._FIGURE_REGION_TYPES:
            return "figure"
        if region.region_type is RegionType.TABLE:
            return "table"
        return "content"

    def _region_index(self, regions: tuple[DocumentRegion, ...], target: DocumentRegion) -> int:
        for index, region in enumerate(regions):
            if region == target:
                return index
        raise PipelineStageError("Structured question references an unknown region")
