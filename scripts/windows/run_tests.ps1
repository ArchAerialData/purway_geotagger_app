param(
    [switch]$UseVenv = $true
)

$ErrorActionPreference = "Stop"

$RepoDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$VenvDir = Join-Path $RepoDir ".venv"

if ($UseVenv) {
    $activate = Join-Path $VenvDir "Scripts\Activate.ps1"
    if (-not (Test-Path $activate)) {
        throw "Venv not found. Run: powershell -ExecutionPolicy Bypass -File scripts\\windows\\setup_windows.ps1"
    }
    & $activate
}

$env:PYTHONPATH = "$RepoDir\src;$env:PYTHONPATH"
python -m compileall "$RepoDir\src"
python -m pytest
