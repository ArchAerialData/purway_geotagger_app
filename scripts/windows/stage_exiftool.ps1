param(
    [string]$Version = $env:EXIFTOOL_VERSION,
    [string]$BuildDir = "build",
    [string]$StageDir = "build/windows_exiftool"
)
$ErrorActionPreference = "Stop"
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot "vendor/exiftool.json") -Raw | ConvertFrom-Json
if ($Version -ne $manifest.version) { throw "Unsupported ExifTool version '$Version'. Update vendor/exiftool.json and its verified archive together." }
$archive = Join-Path $PSScriptRoot ("vendor/" + $manifest.archive)
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $manifest.sha256) { throw "Vendored ExifTool checksum mismatch." }
$buildRoot = [IO.Path]::GetFullPath($BuildDir)
$stage = [IO.Path]::GetFullPath($StageDir)
if (-not $stage.StartsWith($buildRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "StageDir must be a child of BuildDir."
}
New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null
$temporary = Join-Path $buildRoot ("exiftool-stage-" + [Guid]::NewGuid().ToString("N"))
$backup = Join-Path $buildRoot ("exiftool-previous-" + [Guid]::NewGuid().ToString("N"))
# Every recursive delete/move below is constrained to checked BuildDir children.
foreach ($target in @($temporary, $backup, $stage)) {
    if (-not $target.StartsWith($buildRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw "Unsafe stage path: $target" }
}
try {
    $extract = Join-Path $temporary "extracted"
    Expand-Archive -LiteralPath $archive -DestinationPath $extract
    $source = Join-Path $extract ("exiftool-" + $Version + "_64")
    $candidate = Join-Path $temporary "app"
    New-Item -ItemType Directory -Path $candidate | Out-Null
    Copy-Item -LiteralPath (Join-Path $source "exiftool(-k).exe") -Destination (Join-Path $candidate "exiftool.exe")
    Copy-Item -LiteralPath (Join-Path $source "exiftool_files") -Destination $candidate -Recurse
    $actual = (& (Join-Path $candidate "exiftool.exe") -ver | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $actual -ne $Version) { throw "Staged ExifTool version check failed: $actual" }
    if (Test-Path -LiteralPath $stage) { Move-Item -LiteralPath $stage -Destination $backup }
    try { Move-Item -LiteralPath $candidate -Destination $stage }
    catch {
        if ((Test-Path -LiteralPath $backup) -and -not (Test-Path -LiteralPath $stage)) { Move-Item -LiteralPath $backup -Destination $stage }
        throw
    }
    if (Test-Path -LiteralPath $backup) { Remove-Item -LiteralPath $backup -Recurse -Force }
    Write-Output "Verified and staged ExifTool $Version at: $stage"
}
finally {
    if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Recurse -Force }
}
