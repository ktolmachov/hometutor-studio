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
$baseLauncher = Join-Path $repoRoot "scripts\run_start_workflow.ps1"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Error "Project interpreter not found: $pythonExe"
}

if (-not (Test-Path -LiteralPath $baseLauncher)) {
    Write-Error "Base launcher not found: $baseLauncher"
}

if (-not $PackageId) {
    $detectArgs = @(
        "-c",
        "import sys; sys.path.insert(0, 'scripts'); import start_workflow as sw; s = sw.load_state(None); print(s.get('package') or '')"
    )
    $PackageId = (& $pythonExe @detectArgs).Trim()
}

$launcherArgs = @(
    "-ExecutionPolicy", "Bypass",
    "-File", $baseLauncher,
    "-Mode", $Mode,
    "-TargetAgent", $TargetAgent
)

if ($PackageId) {
    $launcherArgs += @("-PackageId", $PackageId)
}

if ($Force.IsPresent) {
    $launcherArgs += "-Force"
}

Write-Host "E2E launcher package: $PackageId"
Write-Host "Running: powershell $($launcherArgs -join ' ')"

& powershell @launcherArgs
$routerExit = $LASTEXITCODE
if ($routerExit -ne 0) {
    exit $routerExit
}

if ($Mode -eq "dry-run") {
    exit 0
}

if (-not $PackageId) {
    Write-Error "Could not determine PACKAGE_ID after router run."
}

$executionContract = Join-Path $repoRoot "archive\team_artifacts\$PackageId\execution_contract.md"

if (Test-Path -LiteralPath $executionContract) {
    Write-Host "Execution contract present: $executionContract"
    exit 0
}

Write-Error @"
Workflow is not complete yet.
Expected execution contract was not created:
  $executionContract

In execute mode, the agent must continue in the same session:
  1. execute the generated planning prompt,
  2. obtain the final copy-paste execution prompt,
  3. save it to execution_contract.md,
  4. only then stop.
"@
