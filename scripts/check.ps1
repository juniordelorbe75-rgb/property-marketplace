[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$frontendPath = Join-Path $projectRoot "frontend"

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Python virtual environment not found. Create .venv and install requirements.txt first."
}

Write-Host "Running backend tests..."
Push-Location $projectRoot
try {
    & $pythonPath -m unittest discover -s backend/tests
    if ($LASTEXITCODE -ne 0) {
        throw "Backend tests failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

Push-Location $frontendPath
try {
    Write-Host "Running frontend tests..."
    & npm test
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend tests failed with exit code $LASTEXITCODE."
    }

    Write-Host "Running frontend lint..."
    & npm run lint
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend lint failed with exit code $LASTEXITCODE."
    }

    Write-Host "Building production frontend..."
    & npm run build
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend build failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

Write-Host "All project checks passed."
