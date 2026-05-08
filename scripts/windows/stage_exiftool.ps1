param(
    [string]$Version = $env:EXIFTOOL_VERSION,
    [string]$BuildDir = "build",
    [string]$StageDir = "build/windows_exiftool"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Version)) {
    throw "EXIFTOOL_VERSION is required."
}

function Test-ZipArchiveMagic {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }

    $item = Get-Item -LiteralPath $Path
    if ($item.Length -lt 1024) {
        return $false
    }

    $stream = [System.IO.File]::OpenRead($item.FullName)
    try {
        $first = $stream.ReadByte()
        $second = $stream.ReadByte()
        return ($first -eq 0x50 -and $second -eq 0x4B)
    }
    finally {
        $stream.Dispose()
    }
}

function Save-ExifToolZip {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Version,
        [Parameter(Mandatory = $true)]
        [string]$ZipPath
    )

    $urls = @(
        ("https://master.dl.sourceforge.net/project/exiftool/exiftool-$Version" + "_64.zip?viasf=1"),
        ("https://cytranet.dl.sourceforge.net/project/exiftool/exiftool-$Version" + "_64.zip?viasf=1"),
        ("https://sourceforge.net/projects/exiftool/files/exiftool-$Version" + "_64.zip/download"),
        ("https://exiftool.org/exiftool-$Version" + "_64.zip")
    )
    $errors = [System.Collections.Generic.List[string]]::new()

    foreach ($url in $urls) {
        Write-Host "Downloading ExifTool $Version from: $url"
        try {
            if (Test-Path -LiteralPath $ZipPath) {
                Remove-Item -LiteralPath $ZipPath -Force
            }

            Invoke-WebRequest -Uri $url -OutFile $ZipPath -MaximumRedirection 10 -ErrorAction Stop
            if (Test-ZipArchiveMagic -Path $ZipPath) {
                $size = (Get-Item -LiteralPath $ZipPath).Length
                Write-Host "Downloaded ExifTool ZIP ($size bytes)."
                return
            }

            $size = 0
            if (Test-Path -LiteralPath $ZipPath) {
                $size = (Get-Item -LiteralPath $ZipPath).Length
            }
            throw "Downloaded file is not a ZIP archive (size=$size)."
        }
        catch {
            $message = $_.Exception.Message
            $errors.Add("$url -> $message")
            Write-Warning "ExifTool download attempt failed: $message"
            if (Test-Path -LiteralPath $ZipPath) {
                Remove-Item -LiteralPath $ZipPath -Force
            }
        }
    }

    $newLine = [Environment]::NewLine
    $attemptText = ($errors | ForEach-Object { " - $_" }) -join $newLine
    throw "Unable to download ExifTool $Version. Attempts:$newLine$attemptText"
}

New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

$zipPath = Join-Path $BuildDir "exiftool_windows.zip"
Save-ExifToolZip -Version $Version -ZipPath $zipPath

$extractRoot = Join-Path $BuildDir "exiftool_windows"
if (Test-Path -LiteralPath $extractRoot) {
    Remove-Item -LiteralPath $extractRoot -Recurse -Force
}
Expand-Archive -Path $zipPath -DestinationPath $extractRoot -Force

if (Test-Path -LiteralPath $StageDir) {
    Remove-Item -LiteralPath $StageDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $StageDir | Out-Null

# Newer ExifTool Windows archives ship `exiftool(-k).exe` instead of `exiftool.exe`.
$exeItem = Get-ChildItem -Path $extractRoot -Recurse -File -Filter "exiftool.exe" | Select-Object -First 1
if (-not $exeItem) {
    $exeItem = Get-ChildItem -Path $extractRoot -Recurse -File -Filter "exiftool(-k).exe" | Select-Object -First 1
}
if (-not $exeItem) {
    $exeItem = Get-ChildItem -Path $extractRoot -Recurse -File -Filter "exiftool*.exe" | Select-Object -First 1
}
if (-not $exeItem) {
    throw "Missing ExifTool executable in extracted archive under: $extractRoot"
}

$srcExe = $exeItem.FullName
$srcFiles = Join-Path $exeItem.Directory.FullName "exiftool_files"
if (-not (Test-Path -LiteralPath $srcFiles)) {
    $filesItem = Get-ChildItem -Path $extractRoot -Recurse -Directory -Filter "exiftool_files" | Select-Object -First 1
    if (-not $filesItem) {
        throw "Missing exiftool_files in extracted archive under: $extractRoot"
    }
    $srcFiles = $filesItem.FullName
}

# Rename to `exiftool.exe` for command-line use when the archive ships
# `exiftool(-k).exe`.
Copy-Item -Force -LiteralPath $srcExe -Destination (Join-Path $StageDir "exiftool.exe")
Copy-Item -Recurse -Force -LiteralPath $srcFiles -Destination (Join-Path $StageDir "exiftool_files")

Write-Host "Staged ExifTool $Version at: $StageDir"
