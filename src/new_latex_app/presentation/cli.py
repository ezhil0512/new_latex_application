"""Command-line presentation entrypoint."""

from argparse import ArgumentParser, Namespace
from pathlib import Path
import logging

from new_latex_app.application.dto import ProcessDocumentCommand
from new_latex_app.infrastructure.di import Container

logger: logging.Logger = logging.getLogger(__name__)


def build_parser() -> ArgumentParser:
    """Create the command-line parser."""
    parser = ArgumentParser(description="Offline educational document to LaTeX foundation.")
    parser.add_argument(
        "input_path",
        nargs="?",
        type=Path,
        help="Temporary input document path for future processing.",
    )
    return parser


def run(args: Namespace) -> int:
    """Run the CLI command."""
    container = Container.bootstrap()
    if args.input_path is None:
        logger.info("CLI help requested")
        build_parser().print_help()
        return 0
    service = container.document_processing_service()
    command = ProcessDocumentCommand(input_path=args.input_path, original_filename=args.input_path.name)
    service.process(command)
    logger.info("CLI processing completed")
    return 0


def main() -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
