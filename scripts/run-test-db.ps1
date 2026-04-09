$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RootDir "backend"
$DataDir = Join-Path $BackendDir "data"
$TestDbRelative = "data/elephant_agent_test.db"
$TestDbPath = Join-Path $BackendDir $TestDbRelative
$Port = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "8000" }
$ResetDb = if ($env:BACKEND_RESET_DB) { $env:BACKEND_RESET_DB.ToLower() -eq "true" } else { $true }

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  throw "Python launcher 'py' is not available. Install Python first."
}

$PortInUse = Get-NetTCPConnection -LocalPort ([int]$Port) -State Listen -ErrorAction SilentlyContinue
if ($PortInUse) {
  $OwningProcess = Get-Process -Id $PortInUse[0].OwningProcess -ErrorAction SilentlyContinue
  $ProcessLabel = if ($OwningProcess) { "$($OwningProcess.ProcessName) (PID $($OwningProcess.Id))" } else { "another process" }
  throw ("Port $Port is already in use by $ProcessLabel. Stop it first or run with " +
    '$env:BACKEND_PORT="8010"; .\scripts\run-test-db.ps1')
}

if ($ResetDb -and (Test-Path -LiteralPath $TestDbPath)) {
  Remove-Item -LiteralPath $TestDbPath -Force
}

$env:DATABASE_PATH = $TestDbRelative
$env:ALLOW_DRY_RUN = if ($env:ALLOW_DRY_RUN) { $env:ALLOW_DRY_RUN } else { "true" }

Write-Host "Starting Elephant Agent backend with test database:"
Write-Host "  $TestDbPath"
Write-Host "Reset DB on start: $ResetDb"
Write-Host "Backend URL: http://127.0.0.1:$Port"

Push-Location $BackendDir
try {
  py -m uvicorn app.main:app --reload --host 127.0.0.1 --port $Port
} finally {
  Pop-Location
}
