param(
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment = "dev",
    [switch]$RunMigrations
)

$ErrorActionPreference = "Stop"

function Import-DotEnvFile {
    param([Parameter(Mandatory = $true)][string]$Path)

    Get-Content -Path $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }

        $delimiterIndex = $line.IndexOf("=")
        if ($delimiterIndex -lt 1) {
            return
        }

        $key = $line.Substring(0, $delimiterIndex).Trim()
        $value = $line.Substring($delimiterIndex + 1).Trim()

        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        Set-Item -Path "Env:$key" -Value $value
    }
}

$rootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envFile = Join-Path $rootDir ".env.$Environment"
if (-not (Test-Path $envFile)) {
    $envFile = Join-Path $rootDir ".env"
}

if (-not (Test-Path $envFile)) {
    Write-Error "No env file found. Expected '$rootDir/.env.$Environment' or '$rootDir/.env'. Create one from '.env.example' first."
}

Write-Host "Loading env from $envFile"
Import-DotEnvFile -Path $envFile

Set-Location (Join-Path $rootDir "backend")

$activateScript = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
}

$pythonExe = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

if ($RunMigrations) {
    Write-Host "Running Alembic migrations..."
    & $pythonExe -m alembic upgrade head
}

Write-Host "Starting backend with environment '$Environment'..."
& $pythonExe -m uvicorn app.main:app --reload --port 8000
