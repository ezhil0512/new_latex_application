"""Concrete rule engine adapter for structured document normalization."""

import logging
import re
import time
from typing import Any

from new_latex_app.domain.entities import BoundingBox, DocumentRegion, DocumentStructure, RecognizedContent
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError

logger: logging.Logger = logging.getLogger(__name__)


class MetadataRuleEngine:
    """Normalize structure analyzer output for deterministic LaTeX generation."""

    _OPTION_LABEL_PATTERN = re.compile(r"^\s*(?:\(([a-dA-D])\)|([a-dA-D])[\).])\s+(.+)$")

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

        updated_contents, updated_regions, index_map = self._normalize_contents(structure)
        metadata = self._remap_question_references(structure.metadata, updated_contents, updated_regions, index_map)

        structure = DocumentStructure(
            title=structure.title,
            pages=structure.pages,
            regions=updated_regions,
            contents=updated_contents,
            metadata=metadata,
        )

        questions = self._normalize_questions(structure)

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

    def _normalize_contents(
        self,
        structure: DocumentStructure,
    ) -> tuple[tuple[RecognizedContent, ...], tuple[DocumentRegion, ...], dict[int, tuple[int, ...]]]:
        """Return content normalized for rule construction without changing upstream stage contracts."""
        contents: list[RecognizedContent] = []
        regions: list[DocumentRegion] = list(structure.regions)
        index_map: dict[int, tuple[int, ...]] = {}

        for original_index, content in enumerate(structure.contents):
            math_metadata = {
                key: value
                for key, value in content.metadata.items()
                if any(token in key.lower() for token in ("math", "ocr", "latex", "formula"))
            }
            content = self._with_reconstructed_text(content)
            expanded = self._expand_spatial_options(content)
            mapped_indices: list[int] = []
            for expanded_content in expanded:
                if expanded_content.region not in regions:
                    regions.append(expanded_content.region)
                mapped_indices.append(len(contents))
                contents.append(expanded_content)
            index_map[original_index] = tuple(mapped_indices)

        return tuple(contents), tuple(regions), index_map

    def _with_reconstructed_text(self, content: RecognizedContent) -> RecognizedContent:
        """Consume reconstructed lines if present in content metadata."""
        reconstructed_lines = content.metadata.get("reconstructed_lines")
        if reconstructed_lines is None:
            return content

        reconstructed_text = "\n".join(
            line["text"] for line in reconstructed_lines if isinstance(line, dict) and "text" in line
        )
        return RecognizedContent(
            region=content.region,
            latex=content.latex,
            text=reconstructed_text,
            asset_path=content.asset_path,
            metadata=content.metadata,
        )

    def _expand_spatial_options(self, content: RecognizedContent) -> tuple[RecognizedContent, ...]:
        """Expand option-like spatial blocks into existing option content shape."""
        if content.region.region_type is not RegionType.TEXT:
            return (content,)

        spatial_blocks = content.metadata.get("spatial_blocks")
        if not isinstance(spatial_blocks, list):
            return (content,)

        option_blocks: list[tuple[dict[str, Any], str, str]] = []
        paragraph_parts: list[str] = []

        for block in spatial_blocks:
            if not isinstance(block, dict) or not isinstance(block.get("text"), str):
                continue
            block_text = block["text"].strip()
            option_match = self._OPTION_LABEL_PATTERN.match(block_text)
            if option_match:
                option_matches = list(
                    re.finditer(r"(?:^|\s)(?:\(([a-dA-D])\)|([a-dA-D])[\).])\s+", block_text)
                )
                if len(option_matches) > 1:
                    for index, split_match in enumerate(option_matches):
                        label = (split_match.group(1) or split_match.group(2) or "").lower()
                        next_match = option_matches[index + 1] if index + 1 < len(option_matches) else None
                        option_text = block_text[split_match.end() : next_match.start() if next_match else None].strip()
                        if option_text:
                            option_blocks.append((block, label, option_text))
                else:
                    label = (option_match.group(1) or option_match.group(2) or "").lower()
                    option_text = option_match.group(3).strip()
                    option_blocks.append((block, label, option_text))
            elif block_text:
                paragraph_parts.append(block_text)

        if len(option_blocks) < 2:
            return (content,)

        expanded: list[RecognizedContent] = []
        paragraph_text = "\n".join(paragraph_parts).strip()
        if paragraph_text:
            expanded.append(
                RecognizedContent(
                    region=content.region,
                    latex=content.latex,
                    text=paragraph_text,
                    asset_path=content.asset_path,
                    metadata=content.metadata,
                )
            )

        for block, label, option_text in option_blocks:
            region = self._option_region(content.region, block, label)
            metadata = dict(content.metadata)
            metadata["option_label"] = label
            metadata["source_spatial_block"] = block
            expanded.append(
                RecognizedContent(
                    region=region,
                    latex=None,
                    text=option_text,
                    asset_path=None,
                    metadata=metadata,
                )
            )

        return tuple(expanded)

    def _option_region(self, source_region: DocumentRegion, block: dict[str, Any], label: str) -> DocumentRegion:
        bbox = self._block_bbox(block) or source_region.bbox
        metadata = dict(source_region.metadata)
        metadata["option_label"] = label
        metadata["source_region_type"] = source_region.region_type.value
        return DocumentRegion(
            page_number=source_region.page_number,
            region_type=RegionType.OPTION,
            bbox=bbox,
            confidence=source_region.confidence,
            metadata=metadata,
        )

    def _block_bbox(self, block: dict[str, Any]) -> BoundingBox | None:
        bbox = block.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            return None
        if not all(isinstance(point, (list, tuple)) and len(point) >= 2 for point in bbox):
            return None
        try:
            xs = [float(point[0]) for point in bbox]
            ys = [float(point[1]) for point in bbox]
        except (TypeError, ValueError):
            return None
        return BoundingBox(x=min(xs), y=min(ys), width=max(xs) - min(xs), height=max(ys) - min(ys))

    def _remap_question_references(
        self,
        metadata: dict[str, Any],
        contents: tuple[RecognizedContent, ...],
        regions: tuple[DocumentRegion, ...],
        index_map: dict[int, tuple[int, ...]],
    ) -> dict[str, Any]:
        remapped_metadata = dict(metadata)
        remapped_questions = []
        for question in tuple(metadata["questions"]):
            remapped_question = dict(question)
            content_indices = tuple(
                mapped_index
                for original_index in question["content_indices"]
                for mapped_index in index_map[int(original_index)]
            )
            remapped_question["content_indices"] = content_indices
            remapped_question["region_indices"] = tuple(
                self._region_index(regions, contents[index].region) for index in content_indices
            )
            remapped_questions.append(remapped_question)
        remapped_metadata["questions"] = tuple(remapped_questions)
        return remapped_metadata

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
