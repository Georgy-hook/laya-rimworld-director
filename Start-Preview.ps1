$ErrorActionPreference = 'Stop'
$configPath = Join-Path $PSScriptRoot 'laya-control.json'
$config = if (Test-Path -LiteralPath $configPath) { Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json } else { $null }
$python = if ($config -and $config.python_exe) { [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot $config.python_exe)) } else { Join-Path $PSScriptRoot '.venv\Scripts\python.exe' }
$bridge = Join-Path $PSScriptRoot 'rimworld_laya.py'
$apiUrl = if ($config -and $config.api_url) { [string]$config.api_url } else { 'http://localhost:8765' }
$interval = if ($config -and $config.interval) { [int]$config.interval } else { 15 }

if (-not (Test-Path -LiteralPath $python)) {
    throw "Laya virtual environment not found: $python"
}

& $python $bridge --api-url $apiUrl watch --interval $interval
