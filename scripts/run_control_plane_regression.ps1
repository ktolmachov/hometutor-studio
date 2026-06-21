param(
    [switch]$FullPytest,
    [switch]$AppSmokeE2E,
    [switch]$NightlyE2E,
    [string]$ReportPath
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

$ReportItems = New-Object System.Collections.Generic.List[object]
$StartedAt = Get-Date

if (-not $ReportPath) {
    $ReportDir = Join-Path $Root "archive\team_artifacts\_regression"
    New-Item -ItemType Directory -Force $ReportDir | Out-Null
    $Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $ReportPath = Join-Path $ReportDir "control_plane_$Stamp.json"
} else {
    $ReportDir = Split-Path -Parent $ReportPath
    if ($ReportDir) {
        New-Item -ItemType Directory -Force $ReportDir | Out-Null
    }
}

function Write-Report {
    param(
        [Parameter(Mandatory = $true)][string]$Status,
        [string]$FailedStep = ""
    )

    $payload = [ordered]@{
        status = $Status
        failed_step = $FailedStep
        started_at = $StartedAt.ToUniversalTime().ToString("o")
        finished_at = (Get-Date).ToUniversalTime().ToString("o")
        root = [string]$Root
        python = [string]$Python
        options = [ordered]@{
            full_pytest = [bool]$FullPytest
            app_smoke_e2e = [bool]$AppSmokeE2E
            nightly_e2e = [bool]$NightlyE2E
        }
        steps = $ReportItems
    }
    $payload | ConvertTo-Json -Depth 8 | Set-Content -Path $ReportPath -Encoding UTF8
}

function Run-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Command
    )

    Write-Host ""
    Write-Host "========================================================================"
    Write-Host "  $Name"
    Write-Host "========================================================================"
    $stepStart = Get-Date
    & $Command
    $exitCode = if ($LASTEXITCODE -eq $null) { 0 } else { [int]$LASTEXITCODE }
    $ReportItems.Add([ordered]@{
        name = $Name
        exit_code = $exitCode
        started_at = $stepStart.ToUniversalTime().ToString("o")
        finished_at = (Get-Date).ToUniversalTime().ToString("o")
        duration_s = [Math]::Round(((Get-Date) - $stepStart).TotalSeconds, 3)
    }) | Out-Null
    if ($exitCode -ne 0) {
        Write-Report -Status "failed" -FailedStep $Name
        throw "$Name failed with exit code $exitCode"
    }
}

$ControlPlaneTests = @(
    "tests/test_failure_classifier.py",
    "tests/test_pipeline_events.py",
    "tests/test_run_autonomous_result_json.py",
    "tests/test_pipeline_status.py",
    "tests/test_quality_gates.py",
    "tests/test_pipeline_guard_hook.py",
    "tests/test_pipeline_guard_logic.py",
    "tests/test_pipeline_lock.py",
    "tests/test_hitl_approval.py",
    "tests/test_proof_bundle.py",
    "tests/test_close_package_guards.py",
    "tests/test_run_autonomous_agent_chain.py",
    "tests/test_adversarial_eval.py",
    "tests/test_prompt_routing_registry.py",
    "tests/test_skills_router.py",
    "tests/test_prompt_utils.py",
    "tests/test_write_set_check.py"
)

Run-Step "Control-plane pytest coverage" {
    & $Python -m pytest @ControlPlaneTests -v
}

Run-Step "Agent prompt lint" {
    & $Python scripts/lint_agent_prompts.py
}

Run-Step "LLM context regression gate" {
    & $Python scripts/check_llm_context_gate.py
}

Run-Step "Backlog drift regression gate" {
    & $Python scripts/check_backlog_drift.py
}

Run-Step "Backlog registry strict lint" {
    & $Python scripts/backlog_registry_lint.py --strict
}

Run-Step "Policy JSON structural checks" {
    & $Python -m json.tool policies/failure_classes.yaml | Out-Null
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $Python -m json.tool policies/adversarial_eval_cases.yaml | Out-Null
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $Python -m json.tool policies/prompts_registry.yaml | Out-Null
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $Python -m json.tool policies/skills_router.yaml | Out-Null
}

if ($FullPytest) {
    Run-Step "Full pytest regression suite" {
        & $Python -m pytest tests/ --tb=short
    }
}

if ($AppSmokeE2E) {
    Run-Step "Playwright offline smoke e2e" {
        npm run test:e2e:smoke
    }
} else {
    Write-Host ""
    Write-Host "========================================================================"
    Write-Host "  Browser e2e"
    Write-Host "========================================================================"
    Write-Host "Skipped by default: this control-plane change is covered by script/API tests."
    Write-Host "Run with -AppSmokeE2E to execute the full app smoke suite."
}

if ($NightlyE2E) {
    Run-Step "Playwright nightly e2e" {
        npm run test:e2e:nightly
    }
}

Write-Host ""
Write-Host "========================================================================"
Write-Host "  PASS: control-plane regression complete"
Write-Host "========================================================================"
Write-Report -Status "passed"
Write-Host "Report: $ReportPath"
