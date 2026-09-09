param(
    [ValidateRange(1, 65535)]
    [int]$Port = 55432
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $projectRoot ".runtime\postgresql"
$binaryRoot = Join-Path $runtimeRoot "pgsql\bin"
$dataRoot = Join-Path $runtimeRoot "data"
$readyCommand = Join-Path $binaryRoot "pg_isready.exe"
$serverCommand = Join-Path $binaryRoot "postgres.exe"

if (-not (Test-Path -LiteralPath $serverCommand)) {
    throw "The project-local PostgreSQL runtime is not installed."
}

& $readyCommand -h 127.0.0.1 -p $Port *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Output "PostgreSQL is already accepting connections on 127.0.0.1:$Port."
    exit 0
}

$processArguments = @("-D", $dataRoot, "-p", [string]$Port, "-h", "127.0.0.1")
Start-Process `
    -FilePath $serverCommand `
    -ArgumentList $processArguments `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $runtimeRoot "postgres.stdout.log") `
    -RedirectStandardError (Join-Path $runtimeRoot "postgres.stderr.log")

for ($attempt = 0; $attempt -lt 20; $attempt++) {
    Start-Sleep -Milliseconds 250
    & $readyCommand -h 127.0.0.1 -p $Port *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Output "PostgreSQL started on 127.0.0.1:$Port."
        exit 0
    }
}

throw "PostgreSQL did not become ready. Check .runtime/postgresql/postgres.stderr.log."
