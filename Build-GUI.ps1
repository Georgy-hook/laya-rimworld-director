param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildEnvironment = Join-Path $projectRoot ".build-venv"
$builder = Join-Path $buildEnvironment "Scripts\python.exe"
$asset = Join-Path $projectRoot "assets\gui\laya-orbit-mascot.png"
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
        "--add-data", "$asset;assets\gui",
        "--icon", $asset
    )

    & $builder -m PyInstaller @shared --name "Laya-Control-Center" (Join-Path $projectRoot "laya_control.py")
    if ($LASTEXITCODE -ne 0) { throw "Laya Control Center build failed." }

    & $builder -m PyInstaller @shared --name "Laya-Setup" (Join-Path $projectRoot "laya_setup.py")
    if ($LASTEXITCODE -ne 0) { throw "Laya Setup build failed." }

    Write-Host "GUI executables are ready in $distribution"
}
finally {
    Pop-Location
}
