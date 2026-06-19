param(
    [string]$PythonLauncher = "py -3.10",
    [string]$VenvPath = ".venv-validation",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

Write-Host "Creating validation environment with Python 3.10"
& $PythonLauncher.Split(" ")[0] $PythonLauncher.Split(" ")[1] -m venv $VenvPath

$python = Join-Path $VenvPath "Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Validation Python was not created at $python"
}

& $python -m pip install --upgrade pip==24.3.1 setuptools==75.6.0 wheel==0.45.1

if (-not $SkipInstall) {
    & $python -m pip install --no-cache-dir -r requirements.validation-order.txt
    & $python -m pip check
}

Write-Host "Validation environment ready: $VenvPath"
Write-Host "Run: $python tools\validate_environment.py --report reports\environment_validation_report.md --json-report reports\environment_validation_report.json"
