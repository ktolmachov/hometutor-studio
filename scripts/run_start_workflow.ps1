param(
    [ValidateSet("dry-run", "execute")]
    [string]$Mode = "dry-run",

    [ValidateSet("cursor_ai", "claude_code", "codex")]
    [string]$TargetAgent = "codex",

    [string]$PackageId = "",

    [switch]$Force
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$routerScript = Join-Path $repoRoot "scripts\start_workflow.py"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Error "Project interpreter not found: $pythonExe"
}

if (-not (Test-Path -LiteralPath $routerScript)) {
    Write-Error "Router script not found: $routerScript"
}

$arguments = @($routerScript)

if ($Mode -eq "dry-run") {
    $arguments += "--dry-run"
} else {
    $arguments += @("--agent", $TargetAgent)
}

if ($PackageId) {
    $arguments += @("--package", $PackageId)
}

if ($Force.IsPresent) {
    $arguments += "--force"
}

Write-Host "Using interpreter: $pythonExe"
Write-Host "Running: $pythonExe $($arguments -join ' ')"

& $pythonExe @arguments
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    exit $exitCode
}
