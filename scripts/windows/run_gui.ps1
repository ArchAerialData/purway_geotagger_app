param(
    [switch]$UseVenv = $true
)

$ErrorActionPreference = "Stop"

$RepoDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$VenvDir = Join-Path $RepoDir ".venv"

if ($UseVenv) {
    $activate = Join-Path $VenvDir "Scripts\Activate.ps1"
    if (-not (Test-Path $activate)) {
        throw "Venv not found. Run: powershell -ExecutionPolicy Bypass -File scripts\\setup_windows.ps1"
    }
    & $activate
}

$env:PYTHONPATH = "$RepoDir\src;$env:PYTHONPATH"
python -m purway_geotagger.app
