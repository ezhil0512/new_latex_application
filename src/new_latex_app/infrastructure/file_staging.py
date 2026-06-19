"""Temporary input staging for uploaded documents."""

from pathlib import Path
import logging
import shutil
import time

logger: logging.Logger = logging.getLogger(__name__)


class LocalInputStager:
    """Copy an uploaded input into the UUID temporary workspace."""

    def stage(self, source_path: Path, workspace_path: Path) -> Path:
        """Stage a source file into temporary storage without logging contents."""
        started_at = time.perf_counter()
        logger.info("Input staging started")
        if not source_path.exists() or not source_path.is_file():
            raise FileNotFoundError("Input document not found")
        staged_path = workspace_path / f"input{source_path.suffix.lower()}"
        shutil.copy2(source_path, staged_path)
        logger.info("Input staging completed in %.3fs", time.perf_counter() - started_at)
        return staged_path
