# Developer Guide

## Adding a Pipeline Adapter

1. Add or reuse a domain interface in `src/new_latex_app/domain/ports`.
2. Implement the adapter in `src/new_latex_app/infrastructure/adapters`.
3. Register the adapter in the dependency injection container.
4. Add unit tests for the adapter and application orchestration.

## Logging Rules

Allowed:

- Stage started.
- Stage completed.
- Execution time.
- Errors.
- Warnings.

Forbidden:

- OCR text.
- Uploaded document contents.
- Personal information.
- Cropped image content or paths exposed to external logs.

## Storage Rules

Use `TemporaryWorkspaceManager` for all processing files. Do not write user content under the repository, logs directory, or a database.

## Testing

```bash
pytest
mypy src
ruff check src tests
```
