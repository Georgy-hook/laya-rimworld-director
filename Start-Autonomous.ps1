param(
    [switch]$StartNow
)

$ErrorActionPreference = 'Stop'
$configPath = Join-Path $PSScriptRoot 'laya-control.json'
$config = if (Test-Path -LiteralPath $configPath) { Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json } else { $null }
$python = if ($config -and $config.python_exe) { [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot $config.python_exe)) } else { Join-Path $PSScriptRoot '.venv\Scripts\python.exe' }
$director = Join-Path $PSScriptRoot 'colony_director.py'
$log = Join-Path $PSScriptRoot 'logs\decisions.jsonl'
$state = Join-Path $PSScriptRoot 'logs\colony-state.json'
$pidFile = Join-Path $PSScriptRoot 'logs\director.pid'
$device = if ($config -and $config.device) { [string]$config.device } else { 'cuda' }
$apiUrl = if ($config -and $config.api_url) { [string]$config.api_url } else { 'http://localhost:8765' }
$interval = if ($config -and $config.interval) { [int]$config.interval } else { 10 }

if (-not (Test-Path -LiteralPath $python)) {
    throw "Laya virtual environment not found: $python"
}

if (-not $StartNow) {
    Write-Host 'Load or create a RimWorld colony first.' -ForegroundColor Cyan
    Read-Host 'When the colony map is visible, press Enter to start Laya'
    Start-Sleep -Seconds 5
}
& $python -u $director --device $device --interval $interval --api-url $apiUrl --log $log --state $state --pid-file $pidFile
