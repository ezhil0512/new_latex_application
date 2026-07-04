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

### Sourcing and Configuring Offline PaddleOCR Models

To configure PaddleOCR for completely offline execution without network access, you must manually download the model assets, extract them, place them in the local folder structure, and set the corresponding environment variables.

#### 1. Required Models and Download Links
The following models are expected by the application runtime and environment validation scripts. They can be downloaded directly from Baidu BOS:

* **Document Detection Model** (`PP-OCRv5_server_det`):
  * **URL:** [PP-OCRv5_server_det_infer.tar](https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-OCRv5_server_det_infer.tar)
* **Text Recognition Model** (`en_PP-OCRv5_mobile_rec`):
  * **URL:** [en_PP-OCRv5_mobile_rec_infer.tar](https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/en_PP-OCRv5_mobile_rec_infer.tar)
* **Document Orientation Classification Model** (`PP-LCNet_x1_0_doc_ori`):
  * **URL:** [PP-LCNet_x1_0_doc_ori_infer.tar](https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-LCNet_x1_0_doc_ori_infer.tar)
* **Document Unwarping Model** (`UVDoc`):
  * **URL:** [UVDoc_infer.tar](https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/UVDoc_infer.tar)
* **Text Line Orientation Classification Model** (`PP-LCNet_x1_0_textline_ori`):
  * **URL:** [PP-LCNet_x1_0_textline_ori_infer.tar](https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-LCNet_x1_0_textline_ori_infer.tar)

#### 2. Expected Folder Structure and File Placement
Once downloaded, extract each `.tar` archive. The extracted contents (specifically `inference.pdmodel` and `inference.pdiparams`) must be placed in individual directories.

Place these directories inside the project's models directory using the following exact structure:

```text
c:\Users\ezhil\OneDrive\Desktop\new_latex_app\models\
└── paddleocr/
    ├── PP-OCRv5_server_det/
    │   ├── inference.pdmodel
    │   └── inference.pdiparams
    ├── en_PP-OCRv5_mobile_rec/
    │   ├── inference.pdmodel
    │   └── inference.pdiparams
    ├── PP-LCNet_x1_0_doc_ori/
    │   ├── inference.pdmodel
    │   └── inference.pdiparams
    ├── UVDoc/
    │   ├── inference.pdmodel
    │   └── inference.pdiparams
    └── PP-LCNet_x1_0_textline_ori/
        ├── inference.pdmodel
        └── inference.pdiparams
```

#### 3. Required Environment Variables
Configure the system environment or a `.env` file in the project root containing the absolute paths to the extracted directories:

```env
PADDLEOCR_TEXT_DETECTION_MODEL_DIR="c:/Users/ezhil/OneDrive/Desktop/new_latex_app/models/paddleocr/PP-OCRv5_server_det"
PADDLEOCR_TEXT_RECOGNITION_MODEL_DIR="c:/Users/ezhil/OneDrive/Desktop/new_latex_app/models/paddleocr/en_PP-OCRv5_mobile_rec"
PADDLEOCR_DOC_ORIENTATION_MODEL_DIR="c:/Users/ezhil/OneDrive/Desktop/new_latex_app/models/paddleocr/PP-LCNet_x1_0_doc_ori"
PADDLEOCR_DOC_UNWARPING_MODEL_DIR="c:/Users/ezhil/OneDrive/Desktop/new_latex_app/models/paddleocr/UVDoc"
PADDLEOCR_TEXTLINE_ORIENTATION_MODEL_DIR="c:/Users/ezhil/OneDrive/Desktop/new_latex_app/models/paddleocr/PP-LCNet_x1_0_textline_ori"
```

## Expected System Dependencies

- Windows: Poppler must be installed and on `PATH` for `pdf2image`; TeX Live must provide `pdflatex`.
- Linux/Docker: install `poppler-utils`, TeX Live, `libgl1`, and `libglib2.0-0`.

## Reports

The validator writes:

- `reports/environment_validation_report.md`
- `reports/environment_validation_report.json`
