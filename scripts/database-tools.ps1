function Get-PropertyMarketplaceDatabaseUrl {
    param([string]$ProjectRoot)

    if ($env:DATABASE_URL) {
        return $env:DATABASE_URL
    }

    $envFile = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path -LiteralPath $envFile -PathType Leaf)) {
        throw "DATABASE_URL is not set and .env was not found."
    }

    $line = Get-Content -LiteralPath $envFile | Where-Object {
        $_ -match '^\s*DATABASE_URL\s*='
    } | Select-Object -First 1

    if (-not $line) {
        throw "DATABASE_URL was not found in .env."
    }

    $value = ($line -split '=', 2)[1].Trim()
    if (
        ($value.StartsWith('"') -and $value.EndsWith('"')) -or
        ($value.StartsWith("'") -and $value.EndsWith("'"))
    ) {
        $value = $value.Substring(1, $value.Length - 2)
    }

    if (-not $value) {
        throw "DATABASE_URL is empty."
    }

    return $value
}

function Invoke-WithPostgresDatabaseUrl {
    param(
        [string]$DatabaseUrl,
        [scriptblock]$Action
    )

    $previousValue = $env:PGDATABASE
    try {
        $env:PGDATABASE = $DatabaseUrl
        & $Action
    }
    finally {
        if ($null -eq $previousValue) {
            Remove-Item Env:PGDATABASE -ErrorAction SilentlyContinue
        }
        else {
            $env:PGDATABASE = $previousValue
        }
    }
}
