param(
    [ValidateSet("list", "preflight", "capture", "gifs", "preview", "publish", "validate", "full")]
    [string]$Step = "full",

    [string]$Run = "",

    [string[]]$ScenarioId = @(),

    [switch]$SkipCapture,
    [switch]$SkipGifs,
    [switch]$FastGifs,
    [switch]$DryRun,
    [switch]$ContinueOnError
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$workflow = Join-Path $repoRoot "scripts\demo_workflow.py"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Error "Project interpreter not found: $pythonExe"
}

if (-not (Test-Path -LiteralPath $workflow)) {
    Write-Error "Workflow script not found: $workflow"
}

$argsList = @($workflow, $Step)

if ($Run) {
    $argsList += @("--run", $Run)
}

foreach ($id in $ScenarioId) {
    if ($id) {
        $argsList += @("--scenario-id", $id)
    }
}

if ($DryRun.IsPresent) { $argsList += "--dry-run" }
if ($Step -eq "full" -and $SkipCapture.IsPresent) { $argsList += "--skip-capture" }
if ($Step -eq "full" -and $SkipGifs.IsPresent) { $argsList += "--skip-gifs" }
if ($Step -eq "full" -and $ContinueOnError.IsPresent) { $argsList += "--continue-on-error" }
if ($Step -eq "gifs" -and $FastGifs.IsPresent) { $argsList += "--fast" }

Write-Host "Smart Demo workflow: $Step"
Push-Location $repoRoot
try {
    & $pythonExe @argsList
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
