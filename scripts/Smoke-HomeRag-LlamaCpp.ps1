#requires -Version 5.1
<#
.SYNOPSIS
  Run the reproducible home_rag -> retrieval -> reranker -> llama.cpp smoke gate.
#>
param(
    [string] $ApiBase = "http://127.0.0.1:8080/v1",
    [string] $Model = "qwopus3.6-35b-a3b-v1-mtp"
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$ConfigPath = Join-Path $Root "config.env"
$LogPath = Join-Path $Root "logs\ask_llama_cpp_smoke.jsonl"
$FileName = "урок_1 Введение в концепцию AI-агентов.md"
$RunId = [guid]::NewGuid().ToString("N")
$Question = (
    "Объясни по материалу урока 1, что такое AI-агент. " +
    "Ответь кратко и только по контексту. " +
    "Технический идентификатор smoke $RunId не включай в ответ."
)

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Project interpreter not found: $Python"
}

$ConfigHashBefore = (Get-FileHash -LiteralPath $ConfigPath -Algorithm SHA256).Hash
$ModelsUrl = "$($ApiBase.TrimEnd('/'))/models"
$Models = Invoke-RestMethod -Uri $ModelsUrl -Method Get -TimeoutSec 10
$ModelIds = @($Models.data | ForEach-Object { $_.id })
if ($ModelIds -notcontains $Model) {
    throw "Model '$Model' not found at $ModelsUrl"
}

$ExpectedGrammarOutput = "OK_HOME_RAG_LLAMA_CPP"
$GrammarPayload = @{
    model = $Model
    messages = @(@{ role = "user"; content = "Return the required marker." })
    temperature = 0
    max_tokens = 32
    grammar = "root ::= `"$ExpectedGrammarOutput`""
} | ConvertTo-Json -Depth 8
$GrammarResponse = Invoke-RestMethod `
    -Uri "$($ApiBase.TrimEnd('/'))/chat/completions" `
    -Method Post `
    -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($GrammarPayload)) `
    -TimeoutSec 30
$GrammarContent = [string] $GrammarResponse.choices[0].message.content
if ($GrammarContent.Trim() -ne $ExpectedGrammarOutput) {
    throw "Grammar smoke mismatch: '$GrammarContent'"
}

New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null
Remove-Item -LiteralPath $LogPath -Force -ErrorAction SilentlyContinue

$PreviousEnvironment = @{
    PYTHONUTF8 = $env:PYTHONUTF8
    SIMILARITY_TOP_K = $env:SIMILARITY_TOP_K
    RERANK_TOP_N = $env:RERANK_TOP_N
    ENABLE_LLM_FALLBACK = $env:ENABLE_LLM_FALLBACK
    LLM_MODEL = $env:LLM_MODEL
    QUIZ_LLM_MODEL = $env:QUIZ_LLM_MODEL
}

try {
    $env:PYTHONUTF8 = "1"
    $env:SIMILARITY_TOP_K = "2"
    $env:RERANK_TOP_N = "2"
    $env:ENABLE_LLM_FALLBACK = "false"
    # NB: config.py loads .env with override=True AFTER these env vars are set.
    # If .env ever contains LLM_MODEL, it will silently override -Model and break the assert.
    $env:LLM_MODEL = $Model
    $env:QUIZ_LLM_MODEL = $Model

    $AskOutput = & $Python -E -X utf8 (Join-Path $Root "ask.py") `
        --profile quality `
        --brief `
        --question $Question `
        --file-name $FileName `
        --non-interactive `
        --log $LogPath 2>&1
    $AskExitCode = $LASTEXITCODE
    $AskOutput | ForEach-Object { Write-Host $_ }
    if ($AskExitCode -ne 0) {
        throw "ask.py failed with exit code $AskExitCode"
    }
} finally {
    foreach ($Entry in $PreviousEnvironment.GetEnumerator()) {
        if ($null -eq $Entry.Value) {
            Remove-Item "Env:$($Entry.Key)" -ErrorAction SilentlyContinue
        } else {
            Set-Item "Env:$($Entry.Key)" $Entry.Value
        }
    }
}

if (-not (Test-Path -LiteralPath $LogPath -PathType Leaf)) {
    throw "Smoke log was not created: $LogPath"
}
$Rows = @(Get-Content -LiteralPath $LogPath -Encoding utf8 | Where-Object { $_.Trim() } | ConvertFrom-Json)
if ($Rows.Count -ne 1) {
    throw "Expected one smoke log entry; found $($Rows.Count)"
}
$Last = $Rows[0]
$Debug = $Last.debug
$Failures = @()
if ($Debug.profile -ne "quality") { $Failures += "profile=$($Debug.profile)" }
if ($Debug.retrieval_mode -ne "hybrid") { $Failures += "retrieval_mode=$($Debug.retrieval_mode)" }
if ($Debug.rerank_enabled -ne $true) { $Failures += "rerank_enabled=$($Debug.rerank_enabled)" }
if ($Debug.llm_source -ne "local") { $Failures += "llm_source=$($Debug.llm_source)" }
if ($Debug.llm_model -ne $Model) { $Failures += "llm_model=$($Debug.llm_model)" }
if ($Debug.llm_api_base -ne $ApiBase) { $Failures += "llm_api_base=$($Debug.llm_api_base)" }
if ($Debug.fallback_used -ne $false) { $Failures += "fallback_used=$($Debug.fallback_used)" }
if ([string] $Last.answer -match "<think>") { $Failures += "answer_contains_think=true" }
if (@($Last.sources).Count -lt 1) { $Failures += "sources_count=0" }
if ($Debug.grounded.schema_validated -ne $true) { $Failures += "grounded_schema_validated=false" }
if ($Failures.Count -gt 0) {
    throw "RAG smoke assertions failed: $($Failures -join ', ')"
}

$ConfigHashAfter = (Get-FileHash -LiteralPath $ConfigPath -Algorithm SHA256).Hash
if ($ConfigHashBefore -ne $ConfigHashAfter) {
    throw "config.env changed during smoke"
}

Write-Host ""
Write-Host "HOME_RAG_LLAMA_CPP_SMOKE=PASS" -ForegroundColor Green
Write-Host "profile=quality"
Write-Host "retrieval=hybrid"
Write-Host "reranker=enabled"
Write-Host "model=$Model"
Write-Host "api_base=$ApiBase"
Write-Host "fallback_used=false"
Write-Host "sources=$(@($Last.sources).Count)"
Write-Host "grammar=$ExpectedGrammarOutput"
Write-Host "run_id=$RunId"
Write-Host "grounded_schema_validated=true"
Write-Host "config_unchanged=true"
Write-Host "log=$LogPath"
