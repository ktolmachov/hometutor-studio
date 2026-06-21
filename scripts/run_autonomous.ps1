param(
    [ValidateSet("cursor_ai", "claude_code", "codex")]
    [string]$TargetAgent = "cursor_ai",

    [string]$PackageId = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$scriptPath = Join-Path $repoRoot "scripts\run_autonomous.py"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    # Fallback to system python
    $pythonExe = "python"
}

$launcherArgs = @(
    $scriptPath,
    "--agent", $TargetAgent
)

if ($PackageId) {
    $launcherArgs += @("--package", $PackageId)
}

Write-Host "Running autonomous loop..."
& $pythonExe @launcherArgs
exit $LASTEXITCODE
