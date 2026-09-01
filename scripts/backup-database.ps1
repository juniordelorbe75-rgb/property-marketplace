[CmdletBinding()]
param(
    [string]$OutputDirectory
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "database-tools.ps1")

$pgDump = Get-Command pg_dump -ErrorAction SilentlyContinue
if (-not $pgDump) {
    throw "pg_dump was not found. Install PostgreSQL command-line tools and add them to PATH."
}

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $projectRoot "backups\database"
}
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $resolvedOutput -Force | Out-Null

$databaseUrl = Get-PropertyMarketplaceDatabaseUrl -ProjectRoot $projectRoot
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupPath = Join-Path $resolvedOutput "property-marketplace-$timestamp.dump"
if (Test-Path -LiteralPath $backupPath) {
    throw "Backup already exists: $backupPath"
}

Invoke-WithPostgresDatabaseUrl -DatabaseUrl $databaseUrl -Action {
    & $pgDump.Source --format=custom --no-owner --no-privileges --file=$backupPath
    if ($LASTEXITCODE -ne 0) {
        throw "pg_dump failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path -LiteralPath $backupPath -PathType Leaf)) {
    throw "pg_dump completed without creating the expected backup file."
}

$backup = Get-Item -LiteralPath $backupPath
if ($backup.Length -eq 0) {
    throw "The backup file is empty."
}

Write-Output "Backup created: $($backup.FullName)"
Write-Output "Size: $([math]::Round($backup.Length / 1MB, 2)) MB"
