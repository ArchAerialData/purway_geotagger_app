param([string]$IsccPath = "build/tools/InnoSetup-6.7.4/ISCC.exe")
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "../..")).Path
$compiler = [IO.Path]::GetFullPath($IsccPath)
if (-not (Test-Path -LiteralPath $compiler)) { throw "Inno compiler missing. Run scripts/windows/setup_inno.ps1 first." }
$oldVersion = $env:APP_VERSION
$oldBuild = $env:APP_BUILD_ID
Push-Location -LiteralPath $repoRoot
try {
    $app = Join-Path $repoRoot "dist/windows/PurwayGeotagger"
    $info = Get-Content -LiteralPath (Join-Path $app "build-info.json") -Raw | ConvertFrom-Json
    if ($info.app_version -notmatch '^\d+\.\d+\.\d+$' -or $info.build_id -notmatch '^\d{8}-\d{4}-[a-f0-9]{8}$') { throw "Invalid build identity." }
    if ((Get-FileHash -LiteralPath (Join-Path $app "PurwayGeotagger.exe") -Algorithm SHA256).Hash -ne $info.executable_sha256) { throw "EXE differs from its build manifest." }
    $env:APP_VERSION = $info.app_version
    $env:APP_BUILD_ID = $info.build_id
    & $compiler "scripts/windows/PurwayGeotagger.iss"
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed." }
    $installer = Join-Path $repoRoot ("dist/windows-installer/PurwayGeotagger-Setup-" + $info.app_version + "-" + $info.build_id + ".exe")
    if (-not (Test-Path -LiteralPath $installer)) { throw "Installer output missing: $installer" }
    $hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash
    ($hash + "  " + [IO.Path]::GetFileName($installer)) | Set-Content -LiteralPath ($installer + ".sha256") -Encoding ascii
    Write-Output "Installer: $installer"
}
finally {
    $env:APP_VERSION = $oldVersion
    $env:APP_BUILD_ID = $oldBuild
    Pop-Location
}
