"""Temporary workspace management for non-persistent document processing."""

from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator
from uuid import uuid4
import logging
import time

from new_latex_app.domain.entities import DocumentSession

logger: logging.Logger = logging.getLogger(__name__)


class TemporaryWorkspaceManager:
    """Create UUID-scoped temporary workspaces and delete them automatically."""

    def __init__(self, temp_root: Path | None = None) -> None:
        """Create a temporary workspace manager."""
        self._temp_root = temp_root

    @contextmanager
    def create(self) -> Iterator[DocumentSession]:
        """Yield a document session and delete all temporary files on exit."""
        session_id = uuid4()
        started_at = time.perf_counter()
        logger.info("Temporary workspace creation started")
        with TemporaryDirectory(prefix=f"{session_id}_", dir=self._temp_root) as temp_dir:
            workspace_path = Path(temp_dir)
            logger.info("Temporary workspace creation completed")
            try:
                yield DocumentSession(session_id=session_id, workspace_path=workspace_path)
            finally:
                logger.info(
                    "Temporary workspace cleanup completed in %.3fs",
                    time.perf_counter() - started_at,
                )
