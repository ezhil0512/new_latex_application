#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3.10}"
VENV_PATH="${VENV_PATH:-.venv-validation}"
SKIP_INSTALL="${SKIP_INSTALL:-0}"

echo "Creating validation environment with ${PYTHON_BIN}"
"${PYTHON_BIN}" -m venv "${VENV_PATH}"

PYTHON="${VENV_PATH}/bin/python"
"${PYTHON}" -m pip install --upgrade pip==24.3.1 setuptools==75.6.0 wheel==0.45.1

if [[ "${SKIP_INSTALL}" != "1" ]]; then
  "${PYTHON}" -m pip install --no-cache-dir -r requirements.validation-order.txt
  "${PYTHON}" -m pip check
fi

echo "Validation environment ready: ${VENV_PATH}"
echo "Run: ${PYTHON} tools/validate_environment.py --report reports/environment_validation_report.md --json-report reports/environment_validation_report.json"
