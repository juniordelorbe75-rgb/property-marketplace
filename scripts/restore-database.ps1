[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,

    [switch]$ConfirmRestore
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "database-tools.ps1")

if (-not $ConfirmRestore) {
    throw "Restore replaces database contents. Run again with -ConfirmRestore after verifying the backup file."
}

$resolvedBackup = [System.IO.Path]::GetFullPath($BackupFile)
if (-not (Test-Path -LiteralPath $resolvedBackup -PathType Leaf)) {
    throw "Backup file not found: $resolvedBackup"
}
if ([System.IO.Path]::GetExtension($resolvedBackup) -ne ".dump") {
    throw "Restore accepts only PostgreSQL custom-format .dump files."
}

$pgRestore = Get-Command pg_restore -ErrorAction SilentlyContinue
if (-not $pgRestore) {
    throw "pg_restore was not found. Install PostgreSQL command-line tools and add them to PATH."
}

$databaseUrl = Get-PropertyMarketplaceDatabaseUrl -ProjectRoot $projectRoot
Invoke-WithPostgresDatabaseUrl -DatabaseUrl $databaseUrl -Action {
    & $pgRestore.Source --clean --if-exists --no-owner --no-privileges --exit-on-error $resolvedBackup
    if ($LASTEXITCODE -ne 0) {
        throw "pg_restore failed with exit code $LASTEXITCODE."
    }
}

Write-Output "Database restored from: $resolvedBackup"
