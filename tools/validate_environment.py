"""Validate dependency imports and model initialization without app logic."""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Callable


@dataclass(slots=True)
class CheckResult:
    """Result for a single dependency check."""

    name: str
    category: str
    status: str
    detail: str
    version: str | None = None
    seconds: float = 0.0


def _version(module: Any) -> str | None:
    """Return a module version if available."""
    return str(getattr(module, "__version__", "")) or None


def _run_check(name: str, category: str, func: Callable[[], tuple[str | None, str]]) -> CheckResult:
    """Execute a validation check and convert exceptions into FAIL records."""
    started = perf_counter()
    try:
        version, detail = func()
        status = "PASS"
    except Exception as exc:
        version = None
        status = "FAIL"
        detail = f"{exc.__class__.__name__}: {exc}\n{traceback.format_exc(limit=3)}"
    return CheckResult(
        name=name,
        category=category,
        status=status,
        detail=detail,
        version=version,
        seconds=round(perf_counter() - started, 3),
    )


def import_module_check(import_name: str, display_name: str | None = None) -> CheckResult:
    """Validate that a module imports successfully."""

    def check() -> tuple[str | None, str]:
        module = importlib.import_module(import_name)
        return _version(module), f"Imported {import_name}"

    return _run_check(display_name or import_name, "import", check)


def command_check(command: str, args: list[str]) -> CheckResult:
    """Validate that a system executable is present."""

    def check() -> tuple[str | None, str]:
        path = shutil.which(command)
        if path is None:
            raise FileNotFoundError(f"Missing executable: {command}")
        completed = subprocess.run(
            [path, *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        first_line = (completed.stdout or completed.stderr).splitlines()[0:1]
        return None, f"Found {path}; {' '.join(first_line)}"

    return _run_check(command, "system", check)


def torch_model_check() -> CheckResult:
    """Instantiate a minimal torchvision model without pretrained weights."""

    def check() -> tuple[str | None, str]:
        import torch
        from torchvision.models import resnet18

        model = resnet18(weights=None)
        model.eval()
        return torch.__version__, "Initialized torchvision resnet18 with weights=None"

    return _run_check("torchvision model init", "model", check)


def paddle_check() -> CheckResult:
    """Run Paddle runtime validation."""

    def check() -> tuple[str | None, str]:
        import paddle

        paddle.utils.run_check()
        return paddle.__version__, "paddle.utils.run_check completed"

    return _run_check("PaddlePaddle runtime", "runtime", check)


def paddleocr_model_check() -> CheckResult:
    """Instantiate PaddleOCR without processing documents."""

    def check() -> tuple[str | None, str]:
        import paddleocr
        from paddleocr import PaddleOCR

        model_dirs = {
            "doc_orientation_classify_model_dir": os.getenv("PADDLEOCR_DOC_ORIENTATION_MODEL_DIR"),
            "doc_unwarping_model_dir": os.getenv("PADDLEOCR_DOC_UNWARPING_MODEL_DIR"),
            "textline_orientation_model_dir": os.getenv("PADDLEOCR_TEXTLINE_ORIENTATION_MODEL_DIR"),
            "text_detection_model_dir": os.getenv("PADDLEOCR_TEXT_DETECTION_MODEL_DIR"),
            "text_recognition_model_dir": os.getenv("PADDLEOCR_TEXT_RECOGNITION_MODEL_DIR"),
        }
        provided = {key: value for key, value in model_dirs.items() if value}
        for key, value in provided.items():
            if not Path(value).exists():
                raise FileNotFoundError(f"{key} does not exist: {value}")
        kwargs: dict[str, Any] = {"lang": "en", **provided}
        # PaddleOCR 3.x may initialize/download models. Keep this as an explicit
        # validation step so missing offline assets are reported honestly.
        PaddleOCR(**kwargs)
        if len(provided) != len(model_dirs):
            detail = "PaddleOCR initialized, but not all local model directories were provided"
        else:
            detail = "PaddleOCR initialized with local model directories"
        return _version(paddleocr), detail

    return _run_check("PaddleOCR init", "model", check)


def paddleocr_offline_check() -> CheckResult:
    """Validate that PaddleOCR model paths are configured for offline use."""

    def check() -> tuple[str | None, str]:
        required = {
            "PADDLEOCR_DOC_ORIENTATION_MODEL_DIR": os.getenv("PADDLEOCR_DOC_ORIENTATION_MODEL_DIR"),
            "PADDLEOCR_DOC_UNWARPING_MODEL_DIR": os.getenv("PADDLEOCR_DOC_UNWARPING_MODEL_DIR"),
            "PADDLEOCR_TEXTLINE_ORIENTATION_MODEL_DIR": os.getenv("PADDLEOCR_TEXTLINE_ORIENTATION_MODEL_DIR"),
            "PADDLEOCR_TEXT_DETECTION_MODEL_DIR": os.getenv("PADDLEOCR_TEXT_DETECTION_MODEL_DIR"),
            "PADDLEOCR_TEXT_RECOGNITION_MODEL_DIR": os.getenv("PADDLEOCR_TEXT_RECOGNITION_MODEL_DIR"),
        }
        missing = [name for name, value in required.items() if not value or not Path(value).exists()]
        if missing:
            raise FileNotFoundError("Missing local PaddleOCR model dirs: " + ", ".join(missing))
        return None, "All PaddleOCR local model directories are configured"

    return _run_check("PaddleOCR offline assets", "offline", check)


def pix2text_model_check() -> CheckResult:
    """Instantiate Pix2Text using optional local model configuration."""

    def check() -> tuple[str | None, str]:
        import pix2text
        from pix2text import Pix2Text

        model_dir = os.getenv("PIX2TEXT_MODEL_DIR")
        if model_dir:
            Pix2Text.from_config(model_dir)
            detail = f"Pix2Text initialized from {model_dir}"
        else:
            Pix2Text()
            detail = "Pix2Text initialized with default configuration"
        return _version(pix2text), detail

    return _run_check("Pix2Text init", "model", check)


def doclayout_yolo_model_check() -> CheckResult:
    """Instantiate DocLayout-YOLO from local weights."""

    def check() -> tuple[str | None, str]:
        weights = os.getenv("DOCLAYOUT_YOLO_WEIGHTS")
        if not weights:
            raise FileNotFoundError("Set DOCLAYOUT_YOLO_WEIGHTS to a local .pt file")
        if not Path(weights).exists():
            raise FileNotFoundError(f"DocLayout-YOLO weights not found: {weights}")
        module = importlib.import_module("doclayout_yolo")
        YOLOv10 = getattr(module, "YOLOv10")
        YOLOv10(weights)
        return _version(module), f"DocLayout-YOLO initialized from {weights}"

    return _run_check("DocLayout-YOLO init", "model", check)


def table_transformer_model_check() -> CheckResult:
    """Instantiate Table Transformer from a local model directory."""

    def check() -> tuple[str | None, str]:
        model_dir = os.getenv("TATR_MODEL_DIR")
        if not model_dir:
            raise FileNotFoundError("Set TATR_MODEL_DIR to a local Table Transformer model directory")
        if not Path(model_dir).exists():
            raise FileNotFoundError(f"Table Transformer model directory not found: {model_dir}")
        import transformers
        from transformers import AutoImageProcessor, TableTransformerForObjectDetection

        AutoImageProcessor.from_pretrained(model_dir, local_files_only=True)
        TableTransformerForObjectDetection.from_pretrained(model_dir, local_files_only=True)
        return transformers.__version__, f"Table Transformer initialized from {model_dir}"

    return _run_check("Table Transformer init", "model", check)


def img2table_check() -> CheckResult:
    """Import img2table and validate its public package import."""

    def check() -> tuple[str | None, str]:
        import img2table

        return _version(img2table), "Imported img2table"

    return _run_check("img2table", "import", check)


def opencv_distribution_check() -> CheckResult:
    """Detect multiple cv2-providing distributions."""

    def check() -> tuple[str | None, str]:
        names = [
            "opencv-python",
            "opencv-contrib-python",
            "opencv-python-headless",
            "opencv-contrib-python-headless",
        ]
        installed = []
        for name in names:
            try:
                installed.append(f"{name}=={importlib.metadata.version(name)}")
            except importlib.metadata.PackageNotFoundError:
                continue
        if len(installed) > 1:
            raise RuntimeError(
                "Multiple OpenCV distributions installed; cv2 namespace collision risk: "
                + ", ".join(installed)
            )
        if not installed:
            raise RuntimeError("No OpenCV distribution metadata found")
        return installed[0].split("==", maxsplit=1)[1], installed[0]

    return _run_check("OpenCV distribution uniqueness", "resolver", check)


def collect_results() -> list[CheckResult]:
    """Run all dependency validation checks."""
    results: list[CheckResult] = [
        import_module_check("numpy"),
        import_module_check("cv2", "OpenCV"),
        opencv_distribution_check(),
        import_module_check("PIL", "Pillow"),
        import_module_check("fitz", "PyMuPDF"),
        import_module_check("pdf2image"),
        import_module_check("torch"),
        import_module_check("torchvision"),
        torch_model_check(),
        import_module_check("paddle"),
        paddle_check(),
        import_module_check("paddleocr"),
        paddleocr_model_check(),
        paddleocr_offline_check(),
        import_module_check("pix2text"),
        pix2text_model_check(),
        import_module_check("doclayout_yolo", "DocLayout-YOLO"),
        doclayout_yolo_model_check(),
        img2table_check(),
        import_module_check("transformers"),
        table_transformer_model_check(),
        import_module_check("jinja2", "Jinja2"),
        import_module_check("pylatexenc"),
        import_module_check("yaml", "PyYAML"),
        import_module_check("pydantic"),
        import_module_check("rich"),
        import_module_check("loguru"),
        command_check("pdftoppm", ["-h"]),
        command_check("pdftocairo", ["-h"]),
        command_check("pdflatex", ["--version"]),
    ]
    results.append(pip_check())
    return results


def pip_check() -> CheckResult:
    """Run pip dependency resolver validation."""

    def check() -> tuple[str | None, str]:
        completed = subprocess.run(
            [sys.executable, "-m", "pip", "check"],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (completed.stdout or completed.stderr).strip()
        if completed.returncode != 0:
            raise RuntimeError(output)
        return None, output or "pip check passed"

    return _run_check("pip check", "resolver", check)


def write_reports(results: list[CheckResult], report: Path, json_report: Path) -> None:
    """Write Markdown and JSON validation reports."""
    report.parent.mkdir(parents=True, exist_ok=True)
    json_report.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "platform": {
            "python": sys.version,
            "executable": sys.executable,
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "environment": {
            "HF_HUB_OFFLINE": os.getenv("HF_HUB_OFFLINE"),
            "TRANSFORMERS_OFFLINE": os.getenv("TRANSFORMERS_OFFLINE"),
            "DOCLAYOUT_YOLO_WEIGHTS": os.getenv("DOCLAYOUT_YOLO_WEIGHTS"),
            "TATR_MODEL_DIR": os.getenv("TATR_MODEL_DIR"),
            "PIX2TEXT_MODEL_DIR": os.getenv("PIX2TEXT_MODEL_DIR"),
        },
        "results": [asdict(result) for result in results],
    }
    json_report.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Environment Validation Report",
        "",
        f"- Python: `{sys.version.split()[0]}`",
        f"- Executable: `{sys.executable}`",
        f"- Platform: `{platform.platform()}`",
        "",
        "| Dependency | Category | Status | Version | Seconds | Detail |",
        "|---|---|---:|---|---:|---|",
    ]
    for result in results:
        detail = result.detail.replace("\n", "<br>").replace("|", "\\|")
        lines.append(
            f"| {result.name} | {result.category} | {result.status} | "
            f"{result.version or ''} | {result.seconds:.3f} | {detail} |"
        )
    failures = [result for result in results if result.status != "PASS"]
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Passed: {len(results) - len(failures)}",
            f"- Failed: {len(failures)}",
        ]
    )
    if failures:
        lines.append("- Overall: FAIL")
    else:
        lines.append("- Overall: PASS")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Validate dependency environment.")
    parser.add_argument("--report", type=Path, default=Path("reports/environment_validation_report.md"))
    parser.add_argument("--json-report", type=Path, default=Path("reports/environment_validation_report.json"))
    return parser.parse_args()


def main() -> int:
    """Run validation checks and write reports."""
    args = parse_args()
    results = collect_results()
    write_reports(results, args.report, args.json_report)
    failed = [result for result in results if result.status != "PASS"]
    for result in results:
        print(f"{result.status:4} {result.name} ({result.seconds:.3f}s)")
    print(f"Markdown report: {args.report}")
    print(f"JSON report: {args.json_report}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
