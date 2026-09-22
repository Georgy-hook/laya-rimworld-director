param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildEnvironment = Join-Path $projectRoot ".build-venv"
$builder = Join-Path $buildEnvironment "Scripts\python.exe"
$assetRoot = Join-Path $projectRoot "assets\gui"
$icon = Join-Path $assetRoot "autopilot-emblem.png"
$distribution = Join-Path $projectRoot "dist"

Push-Location $projectRoot
try {
    if (-not (Test-Path -LiteralPath $builder)) {
        & $PythonExe -m venv $buildEnvironment
    }
    & $builder -m pip install -r (Join-Path $projectRoot "requirements-build.txt")

    $shared = @(
        "--noconfirm", "--clean", "--onefile", "--windowed",
        "--distpath", $distribution,
        "--add-data", "$assetRoot;assets\gui",
        "--icon", $icon
    )

    & $builder -m PyInstaller @shared --name "RimWorld-Autopilot" (Join-Path $projectRoot "autopilot_control.py")
    if ($LASTEXITCODE -ne 0) { throw "RimWorld Autopilot build failed." }

    & $builder -m PyInstaller @shared --uac-admin --name "RimWorld-Autopilot-Setup" (Join-Path $projectRoot "autopilot_setup.py")
    if ($LASTEXITCODE -ne 0) { throw "RimWorld Autopilot Setup build failed." }

    Write-Host "GUI executables are ready in $distribution"
}
finally {
    Pop-Location
}
