"""Temporary workspace management interface."""

from contextlib import AbstractContextManager
from typing import Protocol
import logging

from new_latex_app.domain.entities import DocumentSession

logger: logging.Logger = logging.getLogger(__name__)


class WorkspaceManager(Protocol):
    """Create isolated temporary workspaces for processing sessions."""

    def create(self) -> AbstractContextManager[DocumentSession]:
        """Return a context manager that cleans up all temporary files."""
        ...
