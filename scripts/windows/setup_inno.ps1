param([string]$ToolsDir = "build/tools")
$ErrorActionPreference = "Stop"
$tools = [IO.Path]::GetFullPath($ToolsDir)
New-Item -ItemType Directory -Force -Path $tools | Out-Null
$setup = Join-Path $tools "innosetup-6.7.4.exe"
$expected = "A549929319F9120716677C685535CA4671E4B937B5FDC87E2585F32D8EB30E8C"
$url = "https://github.com/jrsoftware/issrc/releases/download/is-6_7_4/innosetup-6.7.4.exe"
if (-not (Test-Path -LiteralPath $setup)) { Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $setup }
if ((Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash -ne $expected) { throw "Inno Setup download checksum mismatch." }
$destination = Join-Path $tools "InnoSetup-6.7.4"
$arguments = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/NOICONS", "/CURRENTUSER", ('/DIR="' + $destination + '"'))
$process = Start-Process -FilePath $setup -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
if ($process.ExitCode -ne 0) { throw "Inno Setup installation failed: $($process.ExitCode)" }
$iscc = Join-Path $destination "ISCC.exe"
if (-not (Test-Path -LiteralPath $iscc)) { throw "Inno Setup compiler missing." }
Write-Output "Compiler: $iscc"
