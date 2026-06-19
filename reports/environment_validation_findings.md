# Dependency Validation Findings

Validation date: 2026-06-18

Environment tested:

- OS: Windows 10 / 11 family, `Windows-10-10.0.26200-SP0`
- Python: `3.10.11`
- Virtual environment: `.venv-validation`
- Dependency file: `requirements.validation-order.txt`

## Result

Overall result: **FAIL for full offline production readiness**.

The environment is **import-compatible** and `pip check` passes, but full model initialization is not yet offline-compliant because local model artifacts were not supplied for Pix2Text, DocLayout-YOLO, Table Transformer, and PaddleOCR offline asset paths.

## Passing Checks

- NumPy import: PASS
- OpenCV import: PASS
- Pillow import: PASS
- PyMuPDF import: PASS
- pdf2image import: PASS
- PyTorch import: PASS
- torchvision import: PASS
- torchvision model initialization with `weights=None`: PASS
- PaddlePaddle import: PASS
- `paddle.utils.run_check()`: PASS
- PaddleOCR import: PASS
- PaddleOCR object initialization: PASS, but used default official model behavior
- Pix2Text import: PASS
- DocLayout-YOLO import: PASS
- img2table import: PASS
- transformers import: PASS
- Jinja2 import: PASS
- pylatexenc import: PASS
- Poppler commands: PASS
- LaTeX command: PASS
- `pip check`: PASS

## Failing Checks

- OpenCV distribution uniqueness: FAIL
  - Installed packages providing `cv2`: `opencv-python`, `opencv-contrib-python`, `opencv-python-headless`.
  - Minimum mitigation applied: pin all three to `4.10.0.84`.
  - Production risk remains because multiple packages share the same `cv2` namespace.

- PaddleOCR offline assets: FAIL
  - PaddleOCR initialized, but local model directories were not supplied.
  - During validation, PaddleOCR reported official model download/cache behavior under `C:\Users\ezhil\.paddlex\official_models`.
  - Required local directories are documented in `docs/environment_validation.md`.

- Pix2Text initialization: FAIL
  - Missing local DocLayout-YOLO model file:
    `C:\Users\ezhil\AppData\Roaming\pix2text\1.1\layout-docyolo\doclayout_yolo_docstructbench_imgsz1024.pt`
  - This is an offline model asset issue, not an import/version issue.

- DocLayout-YOLO initialization: FAIL
  - `DOCLAYOUT_YOLO_WEIGHTS` was not set to a local `.pt` file.

- Table Transformer initialization: FAIL
  - `TATR_MODEL_DIR` was not set to a local Hugging Face model directory.

## Version Conflicts

No resolver-level version conflicts were reported by `pip check`.

Practical conflict discovered:

- `img2table` requires `opencv-contrib-python>=4`.
- `albumentations`, pulled through the layout/formula stack, requires `opencv-python-headless>=4.9.0.80`.
- The project also directly uses OpenCV.
- Result: multiple OpenCV distributions coexist. This is fragile because they share the `cv2` namespace.

Minimum freeze change made:

- Added `opencv-contrib-python==4.10.0.84`.
- Added `opencv-python-headless==4.10.0.84`.
- Kept `opencv-python==4.10.0.84`.

## Platform Notes

Windows:

- Python 3.10.11 worked.
- PyTorch CPU wheels installed correctly.
- PaddlePaddle CPU installed and passed runtime validation.
- Poppler commands were available through MiKTeX in this machine.
- `pdflatex` was available through MiKTeX.
- Offline model directories still need to be bundled.

Linux:

- Expected to work with Python 3.10.x.
- Required system packages: `poppler-utils`, TeX Live, `libgl1`, `libglib2.0-0`.
- Must validate in Docker before accepting Linux as production-ready.

Docker:

- Docker validation artifacts were generated:
  - `Dockerfile.validation`
  - `docker-compose.validation.yml`
- Docker was not built in this run.
- Docker compatibility remains pending until the validation image is built and the same smoke checks run inside the container.

## Minimum Next Steps

1. Bundle local offline model assets under a non-source `models/` directory.
2. Set the required model path environment variables from `docs/environment_validation.md`.
3. Rerun:

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:PADDLE_PDX_MODEL_SOURCE='local'
.\.venv-validation\Scripts\python.exe tools\validate_environment.py --report reports\environment_validation_report.md --json-report reports\environment_validation_report.json
```

4. Build and run Docker validation:

```bash
docker compose -f docker-compose.validation.yml build
docker compose -f docker-compose.validation.yml run --rm dependency-validation
```

5. Decide whether to accept the multiple-OpenCV distribution risk or replace the table/layout combination with adapters that do not force conflicting OpenCV package names.
