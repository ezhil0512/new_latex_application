from pathlib import Path
from tempfile import mkdtemp
import logging
import shutil
import time

from new_latex_app.domain.entities import LatexDocument
from new_latex_app.domain.exceptions import PipelineStageError

logger: logging.Logger = logging.getLogger(__name__)


class TemporaryExportManager:
    """Package LaTeX source and required diagram assets for frontend export."""

    def export(
        self,
        latex_document: LatexDocument,
        asset_metadata: tuple[dict[str, str], ...],
        workspace_path: Path,
    ) -> Path:
        """Create a temporary export package and return its root path."""
        started_at = time.perf_counter()
        logger.info("Export package creation started")

        self._validate_inputs(latex_document, workspace_path)

        try:
            export_root = Path(mkdtemp(prefix="export_"))
        except Exception as error:
            raise PipelineStageError(f"Failed to create export directory: {error}") from error

        try:
            self._write_latex_source(export_root, latex_document)
            self._copy_assets(export_root, asset_metadata, workspace_path)
        except Exception:
            shutil.rmtree(export_root, ignore_errors=True)
            logger.exception("Export package creation failed")
            raise

        logger.info("Export package creation completed in %.3fs", time.perf_counter() - started_at)
        return export_root

    def _validate_inputs(self, latex_document: LatexDocument, workspace_path: Path) -> None:
        if not latex_document or not latex_document.source:
            raise PipelineStageError("Missing LaTeX source for export")
        if not workspace_path or not workspace_path.exists() or not workspace_path.is_dir():
            raise PipelineStageError("Workspace path does not exist")

    def _write_latex_source(self, export_root: Path, latex_document: LatexDocument) -> None:
        target_tex = export_root / "exam.tex"
        try:
            target_tex.write_text(latex_document.source, encoding="utf-8")
        except Exception as error:
            raise PipelineStageError(f"Failed to write LaTeX source: {error}") from error

    def _copy_assets(
        self,
        export_root: Path,
        asset_metadata: tuple[dict[str, str], ...],
        workspace_path: Path,
    ) -> None:
        assets_dir = export_root / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        if not asset_metadata:
            return

        for metadata in asset_metadata:
            asset_filename = metadata.get("asset_filename")
            asset_relpath = metadata.get("asset_relpath")
            if not asset_filename or not asset_relpath:
                raise PipelineStageError("Diagram asset metadata is missing required fields")

            source_asset = workspace_path / asset_relpath
            if not source_asset.exists() or not source_asset.is_file():
                raise PipelineStageError(f"Diagram asset not found: {asset_relpath}")

            destination_asset = assets_dir / asset_filename
            try:
                shutil.copy2(source_asset, destination_asset)
            except Exception as error:
                raise PipelineStageError(f"Failed to copy diagram asset '{asset_filename}': {error}") from error
