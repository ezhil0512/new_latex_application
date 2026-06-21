from pathlib import Path
import logging
import shutil

import pytest

from new_latex_app.domain.entities import LatexDocument
from new_latex_app.domain.exceptions import PipelineStageError
from new_latex_app.infrastructure.adapters.export_manager import TemporaryExportManager

logger: logging.Logger = logging.getLogger(__name__)


def test_export_with_no_diagrams(tmp_path: Path) -> None:
    latex = LatexDocument(source="\\documentclass{article}\\begin{document}Hello\\end{document}", output_path=None)
    manager = TemporaryExportManager()

    export_root = manager.export(latex, (), tmp_path)

    assert export_root.exists()
    assert (export_root / "exam.tex").read_text(encoding="utf-8") == latex.source
    assert (export_root / "assets").exists()
    assert list((export_root / "assets").iterdir()) == []

    shutil.rmtree(export_root)


def test_export_with_one_diagram(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    asset_dir = workspace / "diagram_assets"
    asset_dir.mkdir()
    asset = asset_dir / "diagram_1.png"
    asset.write_text("data", encoding="utf-8")

    latex = LatexDocument(source="\\documentclass{article}\\begin{document}Figure\\end{document}", output_path=None)
    metadata = ({"asset_filename": "diagram_1.png", "asset_relpath": str(asset.relative_to(workspace))},)
    manager = TemporaryExportManager()

    export_root = manager.export(latex, metadata, workspace)

    assert (export_root / "exam.tex").read_text(encoding="utf-8") == latex.source
    assert (export_root / "assets" / "diagram_1.png").read_text(encoding="utf-8") == "data"

    shutil.rmtree(export_root)


def test_export_with_multiple_diagrams(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    assets_dir = workspace / "diagram_assets"
    assets_dir.mkdir()

    asset_a = assets_dir / "diagram_1.png"
    asset_a.write_text("data-a", encoding="utf-8")
    asset_b = assets_dir / "diagram_2.png"
    asset_b.write_text("data-b", encoding="utf-8")

    latex = LatexDocument(source="\\documentclass{article}\\begin{document}Figures\\end{document}", output_path=None)
    metadata = (
        {"asset_filename": "diagram_1.png", "asset_relpath": str(asset_a.relative_to(workspace))},
        {"asset_filename": "diagram_2.png", "asset_relpath": str(asset_b.relative_to(workspace))},
    )
    manager = TemporaryExportManager()

    export_root = manager.export(latex, metadata, workspace)

    assert (export_root / "assets" / "diagram_1.png").read_text(encoding="utf-8") == "data-a"
    assert (export_root / "assets" / "diagram_2.png").read_text(encoding="utf-8") == "data-b"

    shutil.rmtree(export_root)


def test_export_missing_asset_raises(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)

    latex = LatexDocument(source="\\documentclass{article}\\begin{document}Missing\\end{document}", output_path=None)
    metadata = ({"asset_filename": "diagram_1.png", "asset_relpath": "diagram_assets/diagram_1.png"},)
    manager = TemporaryExportManager()

    with pytest.raises(PipelineStageError, match="Diagram asset not found"):
        manager.export(latex, metadata, workspace)


def test_export_missing_latex_source_raises(tmp_path: Path) -> None:
    manager = TemporaryExportManager()

    with pytest.raises(PipelineStageError, match="Missing LaTeX source"):
        manager.export(LatexDocument(source="", output_path=None), (), tmp_path)


def test_export_missing_workspace_raises(tmp_path: Path) -> None:
    manager = TemporaryExportManager()

    with pytest.raises(PipelineStageError, match="Workspace path does not exist"):
        manager.export(LatexDocument(source="\\documentclass{article}\\begin{document}Hi\\end{document}", output_path=None), (), tmp_path / "missing")
