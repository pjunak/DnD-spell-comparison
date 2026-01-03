[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot ".."))
Set-Location $root

$pyinstaller = if ($env:PYINSTALLER -and $env:PYINSTALLER.Trim()) { $env:PYINSTALLER } else { "pyinstaller" }
$buildDir = Join-Path $root "build"
$finalDir = Join-Path $buildDir "LivingScroll"
$finalBackup = Join-Path $buildDir "LivingScroll.prev"
$tempDist = Join-Path $buildDir ".pyi-dist"
$tempWork = Join-Path $buildDir ".pyi-work"

function Write-Log {
    param([string]$Message)
    Write-Host "[build-windows] $Message"
}

function Remove-TempArtifacts {
    Write-Log "Removing temporary build artifacts"
    if (Test-Path $tempDist) {
        Remove-Item -Recurse -Force -LiteralPath $tempDist -ErrorAction SilentlyContinue
    }
    if (Test-Path $tempWork) {
        Remove-Item -Recurse -Force -LiteralPath $tempWork -ErrorAction SilentlyContinue
    }
    if (Test-Path (Join-Path $root "dist")) {
        Remove-Item -Recurse -Force -LiteralPath (Join-Path $root "dist") -ErrorAction SilentlyContinue
    }
    Get-ChildItem -Path $root -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notlike "*\.venv*" } |
        ForEach-Object { Remove-Item -Recurse -Force -LiteralPath $_.FullName -ErrorAction SilentlyContinue }
}

try {
    $buildSucceeded = $false
    if (-not (Test-Path $buildDir)) {
        New-Item -ItemType Directory -Path $buildDir | Out-Null
    }
    if (Test-Path $finalDir) {
        Write-Log "Backing up previous build artifact"
        if (Test-Path $finalBackup) {
            Remove-Item -Recurse -Force -LiteralPath $finalBackup -ErrorAction SilentlyContinue
        }
        Move-Item -LiteralPath $finalDir -Destination $finalBackup
    }
    if (Test-Path $tempDist) {
        Remove-Item -Recurse -Force -LiteralPath $tempDist -ErrorAction SilentlyContinue
    }
    if (Test-Path $tempWork) {
        Remove-Item -Recurse -Force -LiteralPath $tempWork -ErrorAction SilentlyContinue
    }

    if (-not (Get-Command $pyinstaller -ErrorAction SilentlyContinue)) {
        throw "pyinstaller is required but was not found in PATH."
    }

    Write-Log "Running PyInstaller"
    & $pyinstaller --clean --noconfirm --distpath $tempDist --workpath $tempWork LivingScroll.spec

    $artifactSource = Join-Path $tempDist "LivingScroll"
    if (-not (Test-Path $artifactSource)) {
        throw "PyInstaller output not found at $artifactSource"
    }

    if (Test-Path $finalDir) {
        Remove-Item -Recurse -Force -LiteralPath $finalDir -ErrorAction SilentlyContinue
    }
    if ((Get-Item $artifactSource).PSIsContainer) {
        Move-Item -LiteralPath $artifactSource -Destination $finalDir
    }
    else {
        New-Item -ItemType Directory -Path $finalDir -Force | Out-Null
        Move-Item -LiteralPath $artifactSource -Destination $finalDir
    }
    $buildSucceeded = $true
    Write-Log "Build completed. Artifact available in $finalDir"
}
finally {
    if (-not $buildSucceeded -and (Test-Path $finalBackup)) {
        Write-Log "Build failed; restoring previous artifact"
        if (Test-Path $finalDir) {
            Remove-Item -Recurse -Force -LiteralPath $finalDir -ErrorAction SilentlyContinue
        }
        Move-Item -LiteralPath $finalBackup -Destination $finalDir
    }
    if ($buildSucceeded -and (Test-Path $finalBackup)) {
        Remove-Item -Recurse -Force -LiteralPath $finalBackup -ErrorAction SilentlyContinue
    }
    Remove-TempArtifacts
}
