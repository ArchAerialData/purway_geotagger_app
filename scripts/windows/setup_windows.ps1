param(
    [switch]$IncludeDevDeps = $true
)

$ErrorActionPreference = "Stop"

$RepoDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$VenvDir = Join-Path $RepoDir ".venv"

Write-Host "Repo: $RepoDir"

$requirements = Join-Path $RepoDir "requirements.txt"
if (-not (Test-Path $requirements)) {
    throw "requirements.txt not found at $requirements"
}

function Resolve-Python {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return @{ Exe = $py.Source; Args = @("-3.11") } }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return @{ Exe = $python.Source; Args = @() } }
    throw "Python not found. Install Python 3.11+ and re-run."
}

$pyInfo = Resolve-Python
$pyExe = $pyInfo.Exe
$pyArgs = $pyInfo.Args

if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating venv at $VenvDir ..."
    & $pyExe @pyArgs -m venv $VenvDir
} else {
    Write-Host "Using existing venv at $VenvDir"
}

$activate = Join-Path $VenvDir "Scripts\Activate.ps1"
if (-not (Test-Path $activate)) {
    throw "Venv activation script not found at $activate"
}
& $activate

python -m pip install --upgrade pip wheel setuptools
python -m pip install -r $requirements
if ($IncludeDevDeps -and (Test-Path (Join-Path $RepoDir "requirements-dev.txt"))) {
    python -m pip install -r (Join-Path $RepoDir "requirements-dev.txt")
}

Write-Host "Setup complete."
Write-Host "Next: python -m purway_geotagger.app (from activated venv)"
