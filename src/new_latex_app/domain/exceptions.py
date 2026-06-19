"""Domain-specific exceptions for safe pipeline failure handling."""

import logging

logger: logging.Logger = logging.getLogger(__name__)


class NewLatexAppError(Exception):
    """Base exception for the application."""


class ConfigurationError(NewLatexAppError):
    """Raised when configuration cannot be loaded or validated."""


class UnsupportedInputError(NewLatexAppError):
    """Raised when an input file type is not supported."""


class PipelineStageError(NewLatexAppError):
    """Raised when a pipeline stage fails."""


class ValidationError(NewLatexAppError):
    """Raised when generated LaTeX fails validation."""


class CompilationError(NewLatexAppError):
    """Raised when PDF compilation fails."""
