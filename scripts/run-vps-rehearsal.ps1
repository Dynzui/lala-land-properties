param(
    [ValidateRange(1024, 65535)]
    [int]$HttpsPort = 8443,
    [ValidateRange(1024, 65535)]
    [int]$HttpPort = 8080
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeRoot = Join-Path $repositoryRoot ".runtime\vps-rehearsal"
$environmentFile = Join-Path $runtimeRoot ".env.vps"
$backupRoot = Join-Path $runtimeRoot "verified-backup"
$composeFile = Join-Path $repositoryRoot "compose.vps.yaml"
$projectName = "lala-land-vps-rehearsal"

function New-RandomHex {
    param([int]$Bytes = 32)

    $buffer = [byte[]]::new($Bytes)
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($buffer)
    }
    finally {
        $generator.Dispose()
    }
    return (($buffer | ForEach-Object { $_.ToString("x2") }) -join "")
}

function Find-DockerCommand {
    $command = Get-Command docker -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $candidate = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin\docker.exe"
    if (Test-Path -LiteralPath $candidate) {
        return $candidate
    }

    throw "Docker CLI was not found. Install and start Docker Desktop first."
}

function Find-ComposeCommand {
    $candidate = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin\docker-compose.exe"
    if (Test-Path -LiteralPath $candidate) {
        return $candidate
    }

    $command = Get-Command docker-compose -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    throw "Docker Compose was not found. Repair or reinstall Docker Desktop."
}

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$ComposeArguments)

    & $script:composeCommand `
        --project-name $script:projectName `
        --env-file $script:environmentFile `
        -f $script:composeFile `
        @ComposeArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose failed: $($ComposeArguments -join ' ')"
    }
}

if ($HttpPort -eq $HttpsPort) {
    throw "HTTP and HTTPS rehearsal ports must be different."
}

$dockerCommand = Find-DockerCommand
$composeCommand = Find-ComposeCommand
& $dockerCommand info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is installed but its engine is not available. Start Docker Desktop and retry."
}

New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

if (-not (Test-Path -LiteralPath $environmentFile)) {
    $secretKey = New-RandomHex -Bytes 48
    $databasePassword = New-RandomHex -Bytes 32
    $settings = @(
        "APP_ENV_FILE=.runtime/vps-rehearsal/.env.vps"
        "SITE_DOMAIN=localhost:$HttpsPort"
        "HTTP_PORT=$HttpPort"
        "HTTPS_PORT=$HttpsPort"
        "CADDY_HTTPS_PORT=$HttpsPort"
        "DJANGO_SETTINGS_MODULE=lala_land.settings.production"
        "DJANGO_SECRET_KEY=$secretKey"
        "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1"
        "WAGTAILADMIN_BASE_URL=https://localhost:$HttpsPort"
        "DEFAULT_FROM_EMAIL=rehearsal@localhost.invalid"
        "DATABASE_ENGINE=postgresql"
        "POSTGRES_DB=lala_land"
        "POSTGRES_USER=lala_land"
        "POSTGRES_PASSWORD=$databasePassword"
        "POSTGRES_CONN_MAX_AGE=60"
        "EMAIL_HOST=smtp.invalid"
        "EMAIL_PORT=587"
        "EMAIL_HOST_USER=rehearsal"
        "EMAIL_HOST_PASSWORD=rehearsal-only"
        "EMAIL_USE_TLS=true"
        "EMAIL_TIMEOUT=2"
        "SECURE_HSTS_SECONDS=31536000"
    )
    [IO.File]::WriteAllLines($environmentFile, $settings)
}

Set-Location -LiteralPath $repositoryRoot
Write-Host "Validating the production Compose configuration..."
Invoke-Compose -ComposeArguments @("config", "--quiet")

Write-Host "Building the production Django image..."
Invoke-Compose -ComposeArguments @("build", "web")

Write-Host "Starting the isolated PostgreSQL database..."
Invoke-Compose -ComposeArguments @("up", "--detach", "db")

Write-Host "Applying migrations as a separate release step..."
Invoke-Compose -ComposeArguments @("run", "--rm", "web", "python", "manage.py", "migrate", "--noinput")

Write-Host "Starting Django and Caddy..."
Invoke-Compose -ComposeArguments @("up", "--detach", "web", "proxy")

Write-Host "Running Django's production deployment check..."
Invoke-Compose -ComposeArguments @("exec", "-T", "web", "python", "manage.py", "check", "--deploy")

Write-Host "Creating and verifying a database backup..."
Invoke-Compose -ComposeArguments @("exec", "-T", "db", "pg_dump", "--username=lala_land", "--dbname=lala_land", "--format=custom", "--file=/tmp/rehearsal-database.dump")
Invoke-Compose -ComposeArguments @("cp", "db:/tmp/rehearsal-database.dump", (Join-Path $backupRoot "database.dump"))
Invoke-Compose -ComposeArguments @("exec", "-T", "db", "dropdb", "--username=lala_land", "--if-exists", "--force", "lala_land_restore")
Invoke-Compose -ComposeArguments @("exec", "-T", "db", "createdb", "--username=lala_land", "lala_land_restore")
Invoke-Compose -ComposeArguments @("exec", "-T", "db", "pg_restore", "--username=lala_land", "--dbname=lala_land_restore", "--no-owner", "/tmp/rehearsal-database.dump")
$sourceMigrationCount = (& $composeCommand --project-name $projectName --env-file $environmentFile -f $composeFile exec -T db psql --username=lala_land --dbname=lala_land --tuples-only --no-align --command="SELECT count(*) FROM django_migrations").Trim()
$restoredMigrationCount = (& $composeCommand --project-name $projectName --env-file $environmentFile -f $composeFile exec -T db psql --username=lala_land --dbname=lala_land_restore --tuples-only --no-align --command="SELECT count(*) FROM django_migrations").Trim()
if ($sourceMigrationCount -ne $restoredMigrationCount) {
    throw "Database restore verification failed: migration counts differ."
}
Invoke-Compose -ComposeArguments @("exec", "-T", "db", "dropdb", "--username=lala_land", "lala_land_restore")

Write-Host "Creating and verifying an uploaded-media backup..."
Invoke-Compose -ComposeArguments @("exec", "-T", "web", "sh", "-c", "printf rehearsal-media > /var/data/media/rehearsal-marker.txt")
Invoke-Compose -ComposeArguments @("exec", "-T", "web", "tar", "-czf", "/tmp/rehearsal-media.tar.gz", "-C", "/var/data/media", ".")
Invoke-Compose -ComposeArguments @("cp", "web:/tmp/rehearsal-media.tar.gz", (Join-Path $backupRoot "media.tar.gz"))
Invoke-Compose -ComposeArguments @("exec", "-T", "web", "sh", "-c", "rm -rf /tmp/media-restore && mkdir /tmp/media-restore && tar -xzf /tmp/rehearsal-media.tar.gz -C /tmp/media-restore && cmp /var/data/media/rehearsal-marker.txt /tmp/media-restore/rehearsal-marker.txt")

Write-Host "Checking HTTPS and public responses..."
$siteUrl = "https://localhost:$HttpsPort/"
$adminUrl = "https://localhost:$HttpsPort/admin/"
curl.exe --insecure --fail --silent --show-error --retry 12 --retry-delay 2 --output NUL $siteUrl
if ($LASTEXITCODE -ne 0) {
    throw "The public homepage did not return a successful HTTPS response."
}
curl.exe --insecure --fail --silent --show-error --retry 5 --retry-delay 1 --output NUL $adminUrl
if ($LASTEXITCODE -ne 0) {
    throw "The CMS route did not return a successful HTTPS response."
}

Write-Host ""
Write-Host "VPS rehearsal passed."
Write-Host "Public site: $siteUrl"
Write-Host "CMS: $adminUrl"
Write-Host "A browser certificate warning is expected because Caddy uses a local certificate."
Write-Host "The isolated rehearsal containers were left running so you can inspect them in Docker Desktop."
Write-Host "Verified backup artifacts: $backupRoot"
