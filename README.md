# new_latex_app

`new_latex_app` is a production-oriented foundation for a completely offline Image/PDF-to-LaTeX system for educational documents.

This first milestone intentionally does not implement OCR, AI inference, preprocessing, or LaTeX generation. It provides the replaceable architecture, interfaces, configuration, dependency injection, logging, temporary workspace policy, and deployment files needed to build those capabilities safely.

## Principles

- Offline only: no API calls, no cloud services, no paid models.
- Clean Architecture: domain, application, infrastructure, and presentation are separated.
- Temporary processing only: every session uses a UUID-scoped `TemporaryDirectory`.
- No database and no processing history.
- No logging of OCR text, user documents, or personal information.
- Windows and Linux compatible.

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
new-latex-app --help
pytest
```

On Linux/macOS, activate the environment with `source .venv/bin/activate`.

## Current Status

Implemented:

- Project package structure.
- Abstract interfaces for every pipeline stage.
- Domain dataclasses and enums.
- Dependency injection skeleton.
- YAML and `.env` configuration loader.
- Rotating file logging.
- Temporary workspace manager.
- CLI entrypoint placeholder.
- Docker foundation.

Not implemented yet:

- OCR adapters.
- AI model adapters.
- Image preprocessing.
- LaTeX rendering.
- PDF compilation behavior.
