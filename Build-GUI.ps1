param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildEnvironment = Join-Path $projectRoot ".build-venv"
$builder = Join-Path $buildEnvironment "Scripts\python.exe"
$assetRoot = Join-Path $projectRoot "assets\gui"
$icon = Join-Path $assetRoot "autopilot-emblem.png"
$installerIcon = Join-Path $assetRoot "autopilot.ico"
$distribution = Join-Path $projectRoot "dist"
$installerScript = Join-Path $projectRoot "installer\RimWorld-Autopilot.iss"
$assetValidator = Join-Path $projectRoot "tools\validate_gui_assets.py"
$innoCandidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)

Push-Location $projectRoot
try {
    if (-not (Test-Path -LiteralPath $builder)) {
        & $PythonExe -m venv $buildEnvironment
    }
    & $builder -m pip install -r (Join-Path $projectRoot "requirements-build.txt")
    & $builder $assetValidator $assetRoot
    if ($LASTEXITCODE -ne 0) { throw "GUI asset compatibility validation failed." }
    & $builder -c "from PIL import Image; import sys; Image.open(sys.argv[1]).convert('RGBA').save(sys.argv[2], sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])" $icon $installerIcon
    if ($LASTEXITCODE -ne 0) { throw "Windows icon conversion failed." }

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
    $resolvedDistribution = [IO.Path]::GetFullPath($distribution)
    $resolvedRelease = [IO.Path]::GetFullPath($releaseDirectory)
    if (-not $resolvedRelease.StartsWith($resolvedDistribution, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Release directory escaped the dist folder."
    }
    if (Test-Path -LiteralPath $releaseDirectory) {
        Remove-Item -LiteralPath $releaseDirectory -Recurse -Force
    }
    New-Item -ItemType Directory -Path $releaseDirectory -Force | Out-Null
    Get-ChildItem -LiteralPath $projectRoot -File |
        Where-Object { ($_.Extension -in @(".py", ".ps1", ".cmd", ".md", ".txt")) -or ($_.Name -in @("LICENSE", "RIMAPI_UPSTREAM_COMMIT")) } |
        Where-Object { $_.Name -notin @("laya-control.json", "laya-preferences.json", "rimworld-autopilot.json", "autopilot-preferences.json") } |
        Copy-Item -Destination $releaseDirectory -Force
    foreach ($folder in @("assets", "laya_gui", "tools", "vendor")) {
        Copy-Item -LiteralPath (Join-Path $projectRoot $folder) -Destination $releaseDirectory -Recurse -Force
    }
    Get-ChildItem -LiteralPath $releaseDirectory -Directory -Filter "__pycache__" -Recurse |
        Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $releaseDirectory -Directory -Recurse |
        Where-Object { $_.Name -in @("bin", "obj") } |
        Sort-Object FullName -Descending |
        Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $releaseDirectory -File -Filter "*.pyc" -Recurse |
        Remove-Item -Force
    Get-ChildItem -LiteralPath $releaseDirectory -File -Filter "*.pdb" -Recurse |
        Remove-Item -Force
    Copy-Item -LiteralPath (Join-Path $distribution "RimWorld-Autopilot.exe") -Destination $releaseDirectory -Force
    Copy-Item -LiteralPath (Join-Path $distribution "RimWorld-Autopilot-Setup.exe") -Destination $releaseDirectory -Force
    $archive = Join-Path $distribution "rimworld-autopilot-0.0.2.zip"
    Compress-Archive -Path (Join-Path $releaseDirectory "*") -DestinationPath $archive -CompressionLevel Optimal -Force

    $innoCompiler = $innoCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $innoCompiler) {
        throw "Inno Setup 6.7+ is required. Install JRSoftware.InnoSetup with winget."
    }
    & $innoCompiler $installerScript
    if ($LASTEXITCODE -ne 0) { throw "Windows installer build failed." }

    Write-Host "GUI executables, release archive and standard Windows installer are ready in $distribution"
}
finally {
    Pop-Location
}
