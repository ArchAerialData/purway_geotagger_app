param(
    [string]$PythonExe = "python",
    [string]$ExifToolVersion = "13.50"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "../..")).Path
$stagingRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "build/windows-dist"))
# Stable launcher contract: the local Git Bash `methane` alias targets this folder's EXE.
# Promote every successful build here with its full _internal folder; keep staging temporary.
$destination = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "dist/windows/PurwayGeotagger"))
$stamp = [DateTime]::UtcNow.ToString("yyyyMMdd_HHmmss")
$backup = "$destination.previous-$stamp"

# PyInstaller replaces its staging output. All replacement/move paths must be in this repository.
foreach ($targetPath in @($stagingRoot, $destination, $backup)) {
    if (-not $targetPath.StartsWith($repoRoot + [System.IO.Path]::DirectorySeparatorChar,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Build target escaped repository: $targetPath"
    }
}

Push-Location -LiteralPath $repoRoot
try {
    $env:PYTHONDONTWRITEBYTECODE = "1"
    $exifDir = Join-Path $repoRoot "build/windows_exiftool"
    $exifExe = Join-Path $exifDir "exiftool.exe"
    if (-not (Test-Path -LiteralPath $exifExe)) {
        & (Join-Path $PSScriptRoot "stage_exiftool.ps1") -Version $ExifToolVersion -BuildDir "build" -StageDir $exifDir
    }
    $actualVersion = (& $exifExe -ver | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $actualVersion -ne $ExifToolVersion) {
        throw "Expected ExifTool $ExifToolVersion; found $actualVersion"
    }
    $pyInstallerArgs = @(
        "-m", "PyInstaller", "--noconfirm", "--clean", "--name", "PurwayGeotagger",
        "--windowed", "--onedir", "--specpath", "build/pyinstaller/windows",
        "--workpath", "build/pyinstaller/windows/work", "--distpath", $stagingRoot,
        "--paths", (Join-Path $repoRoot "src"),
        "--add-data", "$(Join-Path $repoRoot 'config/default_templates.json');config",
        "--add-data", "$(Join-Path $repoRoot 'config/wind_templates');config/wind_templates",
        "--add-data", "$(Join-Path $repoRoot 'config/exiftool_config.txt');config",
        "--add-data", "$(Join-Path $repoRoot 'assets');assets",
        "--add-binary", "$exifExe;bin",
        "--add-data", "$(Join-Path $exifDir 'exiftool_files');bin/exiftool_files",
        "--collect-all", "tzdata", "src/purway_geotagger/app.py"
    )
    & $PythonExe @pyInstallerArgs
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }
    $stagedApp = Join-Path $stagingRoot "PurwayGeotagger"
    foreach ($relativePath in @("PurwayGeotagger.exe", "_internal/config/default_templates.json",
            "_internal/config/wind_templates", "_internal/config/exiftool_config.txt", "_internal/assets",
            "_internal/bin/exiftool.exe", "_internal/bin/exiftool_files", "_internal/tzdata")) {
        if (-not (Test-Path -LiteralPath (Join-Path $stagedApp $relativePath))) {
            throw "Build is missing $relativePath"
        }
    }
    & (Join-Path $stagedApp "_internal/bin/exiftool.exe") -ver
    if ($LASTEXITCODE -ne 0) { throw "Bundled ExifTool failed." }

    $sourceHashes = @{}
    Get-ChildItem -LiteralPath (Join-Path $repoRoot "src") -Recurse -File -Filter "*.py" | ForEach-Object {
        $relativeName = $_.FullName.Substring($repoRoot.Length + 1).Replace('\', '/')
        $sourceHashes[$relativeName] = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
    }
    $buildInfo = @{
        built_at_utc = [DateTime]::UtcNow.ToString("o")
        git_revision = (& git rev-parse HEAD | Out-String).Trim()
        python = (& $PythonExe --version | Out-String).Trim()
        exiftool_version = $actualVersion
        executable_sha256 = (Get-FileHash -LiteralPath (Join-Path $stagedApp "PurwayGeotagger.exe") -Algorithm SHA256).Hash
        source_sha256 = $sourceHashes
    }
    $buildInfo | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $stagedApp "build-info.json") -Encoding utf8

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    if (Test-Path -LiteralPath $destination) {
        Move-Item -LiteralPath $destination -Destination $backup
    }
    try {
        Move-Item -LiteralPath $stagedApp -Destination $destination
    }
    catch {
        if ((Test-Path -LiteralPath $backup) -and -not (Test-Path -LiteralPath $destination)) {
            Move-Item -LiteralPath $backup -Destination $destination
        }
        throw
    }
    Write-Output "Built: $(Join-Path $destination 'PurwayGeotagger.exe')"
    if (Test-Path -LiteralPath $backup) { Write-Output "Previous build: $backup" }
}
finally {
    Pop-Location
}
