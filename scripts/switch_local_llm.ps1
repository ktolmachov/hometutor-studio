#requires -Version 5.1
<#
.SYNOPSIS
  Switch hometutor between the supported local LLM servers.

.EXAMPLE
  .\scripts\switch_local_llm.ps1 -Profile llama-cpp -ValidateEndpoint

.EXAMPLE
  .\scripts\switch_local_llm.ps1 -Profile lm-studio -DryRun

.EXAMPLE
  .\scripts\switch_local_llm.ps1 -Profile lm-studio -SkipGraph
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("llama-cpp", "lm-studio")]
    [string] $Profile,

    [string] $Model,
    [switch] $ValidateEndpoint,
    [switch] $DryRun,
    [switch] $SkipGraph
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ConfigPath = Join-Path $Root "config.env"
$BackupDirectory = Join-Path $Root "logs\config_backups"

$Profiles = @{
    "llama-cpp" = @{
        ApiBase = "http://127.0.0.1:8080/v1"
        Model = "qwopus3.6-35b-a3b-v1-mtp"
    }
    "lm-studio" = @{
        ApiBase = "http://127.0.0.1:1234/v1"
        Model = "qwen/qwen3.6-27b"
    }
}

function Test-LocalLlmEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string] $ApiBase,
        [Parameter(Mandatory = $true)]
        [string] $Model
    )

    $ModelsUrl = "$($ApiBase.TrimEnd('/'))/models"
    try {
        $Response = Invoke-RestMethod -Uri $ModelsUrl -Method Get -TimeoutSec 10
        $ModelIds = @($Response.data | ForEach-Object { $_.id })
        if ($ModelIds -notcontains $Model) {
            return @{
                Success = $false
                Status = "FAIL (model '$Model' not found at $ModelsUrl)"
            }
        }
        return @{ Success = $true; Status = "PASS ($ModelsUrl)" }
    } catch {
        return @{
            Success = $false
            Status = "FAIL (${ModelsUrl}: $($_.Exception.Message))"
        }
    }
}

if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw "Config file not found: $ConfigPath"
}

$Selected = $Profiles[$Profile]
$SelectedModel = if ($Model) { $Model } else { $Selected.Model }
$Values = [ordered]@{
    LOCAL_LLM_PROFILE = $Profile
    LLM_API_BASE = $Selected.ApiBase
    LLM_MODEL = $SelectedModel
    QUIZ_LLM_MODEL = $SelectedModel
    SSR_LLM_API_BASE = $Selected.ApiBase
    SSR_LLM_MODEL = $SelectedModel
}
if (-not $SkipGraph) {
    $Values["GRAPH_LLM_API_BASE"] = $Selected.ApiBase
    $Values["GRAPH_MODEL"] = $SelectedModel
}

$Content = [System.IO.File]::ReadAllText($ConfigPath)
$Changes = @()
foreach ($Entry in $Values.GetEnumerator()) {
    $Pattern = "(?m)^$([regex]::Escape($Entry.Key))=(.*)$"
    $Matches = [regex]::Matches($Content, $Pattern)
    if ($Matches.Count -ne 1) {
        throw "Expected exactly one $($Entry.Key) entry in config.env; found $($Matches.Count)."
    }

    $CurrentValue = $Matches[0].Groups[1].Value
    if ($CurrentValue -ne $Entry.Value) {
        $Changes += [pscustomobject]@{
            Name = $Entry.Key
            Before = $CurrentValue
            After = $Entry.Value
        }
        $Content = [regex]::Replace($Content, $Pattern, "$($Entry.Key)=$($Entry.Value)")
    }
}

$BackupPath = "none"
$Mode = if ($DryRun) { "DRY RUN" } else { "APPLIED" }
if ($DryRun) {
    if ($Changes.Count -eq 0) {
        Write-Host "No configuration changes required."
    } else {
        Write-Host "Planned changes:" -ForegroundColor Cyan
        foreach ($Change in $Changes) {
            Write-Host "  $($Change.Name): $($Change.Before) -> $($Change.After)"
        }
    }
} elseif ($Changes.Count -gt 0) {
    New-Item -ItemType Directory -Path $BackupDirectory -Force | Out-Null
    $Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss-fff"
    $BackupPath = Join-Path $BackupDirectory "config.env.$Timestamp.$Profile.bak"
    Copy-Item -LiteralPath $ConfigPath -Destination $BackupPath

    $TempPath = "$ConfigPath.tmp.$([guid]::NewGuid().ToString('N'))"
    $ReplaceBackupPath = "$ConfigPath.replace-backup.$([guid]::NewGuid().ToString('N'))"
    $Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    try {
        [System.IO.File]::WriteAllText($TempPath, $Content, $Utf8NoBom)
        [System.IO.File]::Replace($TempPath, $ConfigPath, $ReplaceBackupPath)
    } finally {
        Remove-Item -LiteralPath $TempPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $ReplaceBackupPath -Force -ErrorAction SilentlyContinue
    }
}

$EndpointResult = @{ Success = $true; Status = "SKIPPED" }
if ($ValidateEndpoint) {
    $EndpointResult = Test-LocalLlmEndpoint -ApiBase $Selected.ApiBase -Model $SelectedModel
}

Write-Host ""
Write-Host "Local LLM switch summary" -ForegroundColor Green
Write-Host "Profile: $Profile"
Write-Host "Mode: $Mode"
Write-Host "API base: $($Selected.ApiBase)"
Write-Host "Model: $SelectedModel"
Write-Host "Graph: $(if ($SkipGraph) { 'preserved' } else { 'switched' })"
Write-Host "Backup: $BackupPath"
Write-Host "Endpoint: $($EndpointResult.Status)"

if (-not $EndpointResult.Success) {
    exit 1
}
