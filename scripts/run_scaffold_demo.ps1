param(
    [int]$Number = 0,

    [Parameter(Mandatory = $true)]
    [string]$Slug,

    [Parameter(Mandatory = $true)]
    [string]$Title,

    [string]$Level = "🟢 Первые шаги",
    [int]$Shots = 3,
    [switch]$UpdateOrder,
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$scaffold = Join-Path $repoRoot "scripts\scaffold_demo_scenario.py"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Error "Project interpreter not found: $pythonExe"
}

$argsList = @(
    $scaffold,
    "--slug", $Slug,
    "--title", $Title,
    "--level", $Level,
    "--shots", $Shots
)

if ($Number -gt 0) {
    $argsList += @("--number", $Number)
}
if ($UpdateOrder.IsPresent) { $argsList += "--update-order" }
if ($Force.IsPresent) { $argsList += "--force" }
if ($DryRun.IsPresent) { $argsList += "--dry-run" }

Write-Host "Scaffold Smart Demo: $Slug"
Push-Location $repoRoot
try {
    & $pythonExe @argsList
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
