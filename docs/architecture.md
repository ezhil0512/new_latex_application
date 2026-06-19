# Architecture

The project follows Clean Architecture.

## Layers

### Domain

The domain layer contains pure types and contracts:

- Document/session entities.
- Region, table, figure, formula, and document structure dataclasses.
- Pipeline stage protocols.
- Service interfaces.
- Domain exceptions.

The domain layer must not import infrastructure libraries such as OpenCV, PaddleOCR, PyMuPDF, or Jinja2.

### Application

The application layer coordinates use cases. It owns orchestration, request/response DTOs, and pipeline flow. It depends on domain interfaces, not concrete adapters.

### Infrastructure

The infrastructure layer provides replaceable implementations:

- Configuration loading.
- Logging setup.
- Temporary workspace management.
- Dependency injection container.
- Future OCR, layout, table, compiler, and rendering adapters.

### Presentation

The presentation layer exposes user-facing interfaces such as CLI, API, or UI. It should call application services and avoid business logic.

## Temporary Storage Policy

Every processing request must create an isolated UUID session directory inside a Python `TemporaryDirectory`. The directory is deleted automatically in `finally`/context-manager cleanup even if processing fails.

Generated `output.tex` and `output.pdf` may exist only long enough to stream or return them to the user.

## Pipeline

1. Document Loader
2. Image Preprocessing
3. DocLayout-YOLO
4. Question Segmentation
5. Region Classification
6. AI Model Router
7. Document Structure Analyzer
8. Rule Engine
9. LaTeX Builder
10. Validation Engine
11. PDF Compiler
12. Output
