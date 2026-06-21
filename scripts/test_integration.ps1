param(
    [string[]]$PytestArgs = @("-q")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot

try {
    # В pytest.ini integration исключён по умолчанию, поэтому запускаем через явный маркер.
    $pytestCmd = @(
        "-m", "pytest",
        "-m", "integration",
        "tests/test_integration_retrieval.py"
    ) + $PytestArgs
    Write-Host "Run: python $($pytestCmd -join ' ')"
    & python @pytestCmd
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
