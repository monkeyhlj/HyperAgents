param(
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment = "dev",
    [switch]$Install
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

Set-Location (Join-Path $rootDir "frontend")

if ($Install) {
    Write-Host "Installing frontend dependencies..."
    npm install
}

Write-Host "Starting frontend with environment '$Environment'..."
npm run dev
