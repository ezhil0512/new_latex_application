# Environment Validation Process

This process validates the frozen dependency stack without implementing OCR or application logic.

## Windows

```powershell
.\scripts\install_windows.ps1
.\.venv-validation\Scripts\python.exe tools\validate_environment.py --report reports\environment_validation_report.md --json-report reports\environment_validation_report.json
```

## Linux

```bash
chmod +x scripts/install_linux.sh
./scripts/install_linux.sh
.venv-validation/bin/python tools/validate_environment.py --report reports/environment_validation_report.md --json-report reports/environment_validation_report.json
```

## Docker

```bash
docker compose -f docker-compose.validation.yml build
docker compose -f docker-compose.validation.yml run --rm dependency-validation
```

## Offline Model Assets

Model initialization checks require local weights for components that normally download models:

- `DOCLAYOUT_YOLO_WEIGHTS`: local DocLayout-YOLO `.pt` weights.
- `TATR_MODEL_DIR`: local Table Transformer directory containing Hugging Face model files.
- `PIX2TEXT_MODEL_DIR`: optional local Pix2Text model/config directory.
- `PADDLEOCR_DOC_ORIENTATION_MODEL_DIR`: local PaddleOCR document-orientation model.
- `PADDLEOCR_DOC_UNWARPING_MODEL_DIR`: local PaddleOCR document-unwarping model.
- `PADDLEOCR_TEXTLINE_ORIENTATION_MODEL_DIR`: local PaddleOCR text-line orientation model.
- `PADDLEOCR_TEXT_DETECTION_MODEL_DIR`: local PaddleOCR detection model.
- `PADDLEOCR_TEXT_RECOGNITION_MODEL_DIR`: local PaddleOCR recognition model.

If these are missing, the report must mark the corresponding model initialization as `FAIL`. That is expected until offline model artifacts are bundled.

## Expected System Dependencies

- Windows: Poppler must be installed and on `PATH` for `pdf2image`; TeX Live must provide `pdflatex`.
- Linux/Docker: install `poppler-utils`, TeX Live, `libgl1`, and `libglib2.0-0`.

## Reports

The validator writes:

- `reports/environment_validation_report.md`
- `reports/environment_validation_report.json`
