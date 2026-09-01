[CmdletBinding()]
param(
    [switch]$UpdateEnv
)

$bytes = New-Object byte[] 48
$generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $generator.GetBytes($bytes)
}
finally {
    $generator.Dispose()
}

$secret = [Convert]::ToBase64String($bytes)

if ($UpdateEnv) {
    $projectRoot = Split-Path -Parent $PSScriptRoot
    $envFile = Join-Path $projectRoot ".env"
    if (-not (Test-Path -LiteralPath $envFile -PathType Leaf)) {
        throw ".env was not found at $envFile"
    }

    $lines = Get-Content -LiteralPath $envFile
    $matches = @($lines | Where-Object { $_ -match '^\s*SECRET_KEY\s*=' })
    if ($matches.Count -ne 1) {
        throw ".env must contain exactly one SECRET_KEY entry."
    }

    $updatedLines = $lines | ForEach-Object {
        if ($_ -match '^\s*SECRET_KEY\s*=') {
            "SECRET_KEY=$secret"
        }
        else {
            $_
        }
    }
    $temporaryFile = Join-Path $projectRoot ".env.secret-rotation.tmp"
    try {
        [System.IO.File]::WriteAllLines($temporaryFile, $updatedLines)
        Move-Item -LiteralPath $temporaryFile -Destination $envFile -Force
    }
    finally {
        Remove-Item -LiteralPath $temporaryFile -ErrorAction SilentlyContinue
    }

    Write-Output "SECRET_KEY was securely rotated in .env."
    Write-Output "All existing login tokens are now invalid."
}
else {
    Write-Output "Generated SECRET_KEY (copy this into .env):"
    Write-Output $secret
    Write-Output "Rotating the key signs out all currently logged-in users."
}
