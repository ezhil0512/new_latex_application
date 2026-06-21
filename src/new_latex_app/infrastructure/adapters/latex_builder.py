"""Concrete LaTeX builder adapter for document structure rendering."""

from pathlib import Path
import logging
import re
import time

from new_latex_app.domain.entities import DocumentStructure, LatexDocument, RecognizedContent
from new_latex_app.domain.enums import RegionType
from new_latex_app.domain.exceptions import PipelineStageError

logger: logging.Logger = logging.getLogger(__name__)


class DefaultLatexBuilder:
    """Build compile-ready LaTeX from structured document metadata."""

    def build(self, structure: DocumentStructure, workspace_path: Path) -> LatexDocument:
        """Render the document structure into a LaTeX source string."""
        started_at = time.perf_counter()
        logger.info("LaTeX builder started")

        self._validate_structure(structure)
        title = self._render_title(structure.title)
        body = self._render_body(structure)
        source = self._build_document(title, body)

        logger.info("LaTeX builder completed in %.3fs", time.perf_counter() - started_at)
        return LatexDocument(source=source, output_path=workspace_path / "document.tex")

    def _validate_structure(self, structure: DocumentStructure) -> None:
        if not structure.pages:
            raise PipelineStageError("Cannot build LaTeX for an empty document")
        if not structure.contents:
            raise PipelineStageError("Cannot build LaTeX without recognized contents")
        if not isinstance(structure.metadata, dict):
            raise PipelineStageError("Invalid document metadata for LaTeX builder")
        questions = structure.metadata.get("questions")
        if not isinstance(questions, (tuple, list)) or not questions:
            raise PipelineStageError("Document structure missing question metadata")

        for question in questions:
            if not isinstance(question, dict):
                raise PipelineStageError("Invalid question metadata format")
            if not isinstance(question.get("question_id"), str) or not question["question_id"]:
                raise PipelineStageError("Question metadata is missing a valid identifier")
            if not isinstance(question.get("page_number"), int) or question["page_number"] <= 0:
                raise PipelineStageError("Question metadata contains an invalid page number")
            if not isinstance(question.get("question_index"), int) or question["question_index"] <= 0:
                raise PipelineStageError("Question metadata contains an invalid question index")
            if not isinstance(question.get("blocks"), (tuple, list)) or not question["blocks"]:
                raise PipelineStageError("Question metadata missing block definitions")

    def _render_title(self, title: str | None) -> str:
        if not title:
            return ""
        escaped = self._escape_text(title)
        return f"\\title{{{escaped}}}\n\\maketitle\n"

    def _render_body(self, structure: DocumentStructure) -> str:
        questions = tuple(structure.metadata["questions"])
        body_parts = ["\\section*{Questions}", "\\begin{enumerate}[leftmargin=*]"]
        for question in questions:
            body_parts.append(self._render_question(question, structure))
        body_parts.append("\\end{enumerate}")
        return "\n\n".join(body_parts)

    def _render_question(self, question: dict[str, object], structure: DocumentStructure) -> str:
        question_number = question["question_index"]
        header = f"\\item\\textbf{{Question {question_number}}}"
        blocks = tuple(question["blocks"])
        rendered_blocks = [self._render_block(block, structure) for block in blocks]
        return f"{header}\n\n" + "\n\n".join(rendered_blocks)

    def _render_block(self, block: dict[str, object], structure: DocumentStructure) -> str:
        block_type = block.get("block_type")
        content_indices = tuple(block.get("content_indices", ()))
        if not content_indices:
            raise PipelineStageError("Question block missing content references")

        if block_type == "paragraph":
            return self._render_paragraph(content_indices, structure)
        if block_type == "formula":
            return self._render_display_formula(content_indices, structure)
        if block_type == "option_group":
            return self._render_options(content_indices, structure)
        if block_type == "figure":
            return self._render_figures(content_indices, structure)
        if block_type == "table":
            return self._render_table(content_indices, structure)
        return self._render_paragraph(content_indices, structure)

    def _render_paragraph(self, content_indices: tuple[int, ...], structure: DocumentStructure) -> str:
        text_parts: list[str] = []
        for index in content_indices:
            content = self._get_content(structure, index)
            if content.region.region_type is RegionType.FORMULA:
                text_parts.append(self._render_inline_formula(content))
            else:
                text_parts.append(self._render_text_content(content))
        text = " ".join(part for part in text_parts if part)
        return text.strip() or ""

    def _render_display_formula(self, content_indices: tuple[int, ...], structure: DocumentStructure) -> str:
        if len(content_indices) != 1:
            raise PipelineStageError("Display formula block must contain exactly one formula content")
        content = self._get_content(structure, content_indices[0])
        if content.region.region_type is not RegionType.FORMULA:
            raise PipelineStageError("Display formula block contains non-formula content")
        if not content.latex:
            raise PipelineStageError("Formula content is missing LaTeX source")
        return f"\\[\n{content.latex.strip()}\n\\]"

    def _render_options(self, content_indices: tuple[int, ...], structure: DocumentStructure) -> str:
        options = [self._render_text_content(self._get_content(structure, index)) for index in content_indices]
        items = "\n".join(f"\\item {option}" for option in options)
        return f"\\begin{{enumerate}}[label=(\\alph*)]\n{items}\n\\end{{enumerate}}"

    def _render_figures(self, content_indices: tuple[int, ...], structure: DocumentStructure) -> str:
        figures: list[str] = []
        for index in content_indices:
            content = self._get_content(structure, index)
            if content.region.region_type not in {
                RegionType.FIGURE,
                RegionType.GRAPH,
                RegionType.PHYSICS_DIAGRAM,
                RegionType.BIOLOGY_DIAGRAM,
                RegionType.CHEMICAL_STRUCTURE,
            }:
                raise PipelineStageError("Figure block contains non-diagram content")
            asset_ref = self._resolve_asset_reference(content)
            caption = self._render_text_content(content) if content.text else ""
            figure = ["\\begin{figure}[htbp]", "\\centering", f"\\includegraphics[width=0.95\\linewidth]{{{asset_ref}}}"]
            if caption:
                figure.append(f"\\caption{{{caption}}}")
            figure.append("\\end{figure}")
            figures.append("\n".join(figure))
        return "\n\n".join(figures)

    def _render_table(self, content_indices: tuple[int, ...], structure: DocumentStructure) -> str:
        content = self._get_content(structure, content_indices[0])
        if content.region.region_type is not RegionType.TABLE:
            raise PipelineStageError("Table block contains non-table content")
        text = content.text or ""
        rows = [self._escape_text(row.strip()) for row in text.splitlines() if row.strip()]
        if not rows:
            return ""
        body = " \\\\ \n".join(rows)
        return f"\\begin{{tabular}}{{@{{}}l@{{}}}}\n{body}\\\\\n\\end{{tabular}}"

    def _render_inline_formula(self, content: RecognizedContent) -> str:
        if not content.latex:
            raise PipelineStageError("Inline formula content is missing LaTeX source")
        return f"\\({content.latex.strip()}\\)"

    def _render_text_content(self, content: RecognizedContent) -> str:
        text = content.metadata.get("chemistry", {}).get("normalized_text")
        if text is None:
            text = content.text or ""
        return self._escape_text(text)

    def _resolve_asset_reference(self, content: RecognizedContent) -> str:
        asset_filename = content.metadata.get("asset_filename")
        if asset_filename:
            return f"assets/{asset_filename}"
        if content.asset_path is not None:
            return f"assets/{content.asset_path.name}"
        raise PipelineStageError("Figure content is missing asset reference")

    def _build_document(self, title: str, body: str) -> str:
        preamble = """\\documentclass[11pt]{article}
\\usepackage[utf8]{inputenc}
\\usepackage{amsmath}
\\usepackage{graphicx}
\\usepackage{enumitem}
\\usepackage{booktabs}
\\usepackage{geometry}
\\geometry{margin=1in}
"""
        return f"{preamble}\n{title}\n\\begin{{document}}\n{body}\n\\end{{document}}\n"

    def _get_content(self, structure: DocumentStructure, index: int) -> RecognizedContent:
        try:
            return structure.contents[index]
        except IndexError as error:
            raise PipelineStageError("Question metadata references missing content") from error

    def _escape_text(self, text: str) -> str:
        if not text:
            return ""
        escaped = re.sub(r"(?<!\\)([#$%&])", r"\\\\\1", text)
        return escaped.replace("~", "\\textasciitilde{}")
