param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8000,
    [ValidateRange(1, 65535)]
    [int]$PostgresPort = 55432
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonCandidates = @(
    (Join-Path $repositoryRoot ".venv\Scripts\python.exe"),
    (Join-Path $repositoryRoot "..\..\.venv\Scripts\python.exe")
)
$pythonPath = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $pythonPath) {
    throw "No Python virtual environment was found for this repository."
}

$listenerPattern = "127\.0\.0\.1:$Port\s+0\.0\.0\.0:0\s+LISTENING"
$listenerProcessIds = @(
    netstat -ano |
        Select-String $listenerPattern |
        ForEach-Object {
            if ($_ -match "\s+(\d+)\s*$") {
                [int]$Matches[1]
            }
        } |
        Sort-Object -Unique
)

foreach ($listenerProcessId in $listenerProcessIds) {
    $listenerProcess = Get-Process -Id $listenerProcessId
    if ($listenerProcess.ProcessName -ne "python") {
        throw "Port $Port belongs to $($listenerProcess.ProcessName), so it was not stopped."
    }
    Write-Host "Stopping stale development server process $listenerProcessId on port $Port..."
    Stop-Process -Id $listenerProcessId -Force
}

Start-Sleep -Milliseconds 400
if (netstat -ano | Select-String $listenerPattern) {
    throw "Port $Port is still occupied after cleanup."
}

$env:POSTGRES_PORT = [string]$PostgresPort
$env:WAGTAILADMIN_BASE_URL = "http://127.0.0.1:$Port"
Set-Location -LiteralPath $repositoryRoot
Write-Host "Starting one development server at http://127.0.0.1:$Port/"
& $pythonPath manage.py runserver "127.0.0.1:$Port" --noreload
