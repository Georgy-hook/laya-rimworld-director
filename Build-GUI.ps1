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

    $releaseName = "RimWorld-Autopilot-0.0.2"
    $releaseDirectory = Join-Path $distribution $releaseName
    New-Item -ItemType Directory -Path $releaseDirectory -Force | Out-Null
    Get-ChildItem -LiteralPath $projectRoot -File |
        Where-Object { ($_.Extension -in @(".py", ".ps1", ".cmd", ".md", ".txt")) -or ($_.Name -in @("LICENSE", "RIMAPI_UPSTREAM_COMMIT")) } |
        Where-Object { $_.Name -notin @("laya-control.json", "laya-preferences.json", "rimworld-autopilot.json", "autopilot-preferences.json") } |
        Copy-Item -Destination $releaseDirectory -Force
    foreach ($folder in @("assets", "laya_gui", "vendor")) {
        Copy-Item -LiteralPath (Join-Path $projectRoot $folder) -Destination $releaseDirectory -Recurse -Force
    }
    Copy-Item -LiteralPath (Join-Path $distribution "RimWorld-Autopilot.exe") -Destination $releaseDirectory -Force
    Copy-Item -LiteralPath (Join-Path $distribution "RimWorld-Autopilot-Setup.exe") -Destination $releaseDirectory -Force
    $archive = Join-Path $distribution "rimworld-autopilot-0.0.2.zip"
    Compress-Archive -Path (Join-Path $releaseDirectory "*") -DestinationPath $archive -CompressionLevel Optimal -Force

    Write-Host "GUI executables and release archive are ready in $distribution"
}
finally {
    Pop-Location
}
