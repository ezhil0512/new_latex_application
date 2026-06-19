# Environment Validation Report

- Python: `3.10.11`
- Executable: `C:\Users\ezhil\OneDrive\Desktop\new_latex_app\.venv-validation\Scripts\python.exe`
- Platform: `Windows-10-10.0.26200-SP0`

| Dependency | Category | Status | Version | Seconds | Detail |
|---|---|---:|---|---:|---|
| numpy | import | PASS | 1.26.4 | 0.195 | Imported numpy |
| OpenCV | import | PASS | 4.10.0 | 1.602 | Imported cv2 |
| OpenCV distribution uniqueness | resolver | FAIL |  | 0.011 | RuntimeError: Multiple OpenCV distributions installed; cv2 namespace collision risk: opencv-python==4.10.0.84, opencv-contrib-python==4.10.0.84, opencv-python-headless==4.10.0.84<br>Traceback (most recent call last):<br>  File "C:\Users\ezhil\OneDrive\Desktop\new_latex_app\tools\validate_environment.py", line 42, in _run_check<br>    version, detail = func()<br>  File "C:\Users\ezhil\OneDrive\Desktop\new_latex_app\tools\validate_environment.py", line 247, in check<br>    raise RuntimeError(<br>RuntimeError: Multiple OpenCV distributions installed; cv2 namespace collision risk: opencv-python==4.10.0.84, opencv-contrib-python==4.10.0.84, opencv-python-headless==4.10.0.84<br> |
| Pillow | import | PASS | 10.4.0 | 0.002 | Imported PIL |
| PyMuPDF | import | PASS | 1.24.14 | 0.109 | Imported fitz |
| pdf2image | import | PASS |  | 0.036 | Imported pdf2image |
| torch | import | PASS | 2.5.1+cpu | 3.542 | Imported torch |
| torchvision | import | PASS | 0.20.1+cpu | 3.466 | Imported torchvision |
| torchvision model init | model | PASS | 2.5.1+cpu | 0.221 | Initialized torchvision resnet18 with weights=None |
| paddle | import | PASS | 3.1.1 | 4.955 | Imported paddle |
| PaddlePaddle runtime | runtime | PASS | 3.1.1 | 0.469 | paddle.utils.run_check completed |
| paddleocr | import | PASS | 3.2.0 | 15.530 | Imported paddleocr |
| PaddleOCR init | model | PASS | 3.2.0 | 14.330 | PaddleOCR initialized, but not all local model directories were provided |
| PaddleOCR offline assets | offline | FAIL |  | 0.001 | FileNotFoundError: Missing local PaddleOCR model dirs: PADDLEOCR_DOC_ORIENTATION_MODEL_DIR, PADDLEOCR_DOC_UNWARPING_MODEL_DIR, PADDLEOCR_TEXTLINE_ORIENTATION_MODEL_DIR, PADDLEOCR_TEXT_DETECTION_MODEL_DIR, PADDLEOCR_TEXT_RECOGNITION_MODEL_DIR<br>Traceback (most recent call last):<br>  File "C:\Users\ezhil\OneDrive\Desktop\new_latex_app\tools\validate_environment.py", line 42, in _run_check<br>    version, detail = func()<br>  File "C:\Users\ezhil\OneDrive\Desktop\new_latex_app\tools\validate_environment.py", line 158, in check<br>    raise FileNotFoundError("Missing local PaddleOCR model dirs: " + ", ".join(missing))<br>FileNotFoundError: Missing local PaddleOCR model dirs: PADDLEOCR_DOC_ORIENTATION_MODEL_DIR, PADDLEOCR_DOC_UNWARPING_MODEL_DIR, PADDLEOCR_TEXTLINE_ORIENTATION_MODEL_DIR, PADDLEOCR_TEXT_DETECTION_MODEL_DIR, PADDLEOCR_TEXT_RECOGNITION_MODEL_DIR<br> |
| pix2text | import | PASS | <module 'pix2text.__version__' from 'C:\\Users\\ezhil\\OneDrive\\Desktop\\new_latex_app\\.venv-validation\\lib\\site-packages\\pix2text\\__version__.py'> | 3.216 | Imported pix2text |
| Pix2Text init | model | FAIL |  | 1.125 | FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\ezhil\\AppData\\Roaming\\pix2text\\1.1\\layout-docyolo\\doclayout_yolo_docstructbench_imgsz1024.pt'<br>Traceback (most recent call last):<br>  File "C:\Users\ezhil\OneDrive\Desktop\new_latex_app\tools\validate_environment.py", line 42, in _run_check<br>    version, detail = func()<br>  File "C:\Users\ezhil\OneDrive\Desktop\new_latex_app\tools\validate_environment.py", line 176, in check<br>    Pix2Text()<br>  File "C:\Users\ezhil\OneDrive\Desktop\new_latex_app\.venv-validation\lib\site-packages\pix2text\pix_to_text.py", line 206, in __init__<br>    layout_parser = prepare_layout_engine({}, device=device)<br>FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\ezhil\\AppData\\Roaming\\pix2text\\1.1\\layout-docyolo\\doclayout_yolo_docstructbench_imgsz1024.pt'<br> |
| DocLayout-YOLO | import | PASS | 0.0.4 | 0.000 | Imported doclayout_yolo |
| DocLayout-YOLO init | model | FAIL |  | 0.000 | FileNotFoundError: Set DOCLAYOUT_YOLO_WEIGHTS to a local .pt file<br>Traceback (most recent call last):<br>  File "C:\Users\ezhil\OneDrive\Desktop\new_latex_app\tools\validate_environment.py", line 42, in _run_check<br>    version, detail = func()<br>  File "C:\Users\ezhil\OneDrive\Desktop\new_latex_app\tools\validate_environment.py", line 189, in check<br>    raise FileNotFoundError("Set DOCLAYOUT_YOLO_WEIGHTS to a local .pt file")<br>FileNotFoundError: Set DOCLAYOUT_YOLO_WEIGHTS to a local .pt file<br> |
| img2table | import | PASS |  | 0.001 | Imported img2table |
| transformers | import | PASS | 4.44.2 | 0.000 | Imported transformers |
| Table Transformer init | model | FAIL |  | 0.000 | FileNotFoundError: Set TATR_MODEL_DIR to a local Table Transformer model directory<br>Traceback (most recent call last):<br>  File "C:\Users\ezhil\OneDrive\Desktop\new_latex_app\tools\validate_environment.py", line 42, in _run_check<br>    version, detail = func()<br>  File "C:\Users\ezhil\OneDrive\Desktop\new_latex_app\tools\validate_environment.py", line 206, in check<br>    raise FileNotFoundError("Set TATR_MODEL_DIR to a local Table Transformer model directory")<br>FileNotFoundError: Set TATR_MODEL_DIR to a local Table Transformer model directory<br> |
| Jinja2 | import | PASS | 3.1.6 | 0.000 | Imported jinja2 |
| pylatexenc | import | PASS | 2.10 | 0.002 | Imported pylatexenc |
| PyYAML | import | PASS | 6.0.2 | 0.000 | Imported yaml |
| pydantic | import | PASS | 2.10.6 | 0.000 | Imported pydantic |
| rich | import | PASS |  | 0.000 | Imported rich |
| loguru | import | PASS | 0.7.3 | 0.049 | Imported loguru |
| pdftoppm | system | PASS |  | 0.412 | Found C:\Users\ezhil\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdftoppm.EXE; pdftoppm version 24.04.0 |
| pdftocairo | system | PASS |  | 0.392 | Found C:\Users\ezhil\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdftocairo.EXE; pdftocairo version 24.04.0 |
| pdflatex | system | PASS |  | 0.610 | Found C:\Users\ezhil\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.EXE; MiKTeX-pdfTeX 4.23 (MiKTeX 25.12) |
| pip check | resolver | PASS |  | 2.544 | No broken requirements found. |

## Summary

- Passed: 26
- Failed: 5
- Overall: FAIL
