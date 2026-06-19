"""Generic pipeline contracts."""

from typing import Generic, Protocol, TypeVar
import logging

from new_latex_app.domain.enums import PipelineStageName

logger: logging.Logger = logging.getLogger(__name__)

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class PipelineStage(Protocol, Generic[InputT, OutputT]):
    """A typed, replaceable pipeline stage."""

    @property
    def name(self) -> PipelineStageName:
        """Return the canonical stage name."""
        ...

    def run(self, payload: InputT) -> OutputT:
        """Process a payload and return the next payload."""
        ...
