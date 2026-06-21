param(
    [string]$LlmModel = "qwen2.5:7b-instruct",
    [string]$EmbedModel = "nomic-embed-text",
    [string]$OllamaBaseUrl = "http://127.0.0.1:11434/v1",
    [switch]$SkipPull,
    [string[]]$PytestArgs = @("-q")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Set-EnvOrClear {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [string]$Value
    )
    if ([string]::IsNullOrEmpty($Value)) {
        Remove-Item "Env:$Name" -ErrorAction SilentlyContinue
        return
    }
    Set-Item "Env:$Name" -Value $Value
}

function Ensure-OllamaReachable {
    param(
        [Parameter(Mandatory = $true)][string]$BaseUrl
    )
    $root = if ($BaseUrl.EndsWith("/v1")) {
        $BaseUrl.Substring(0, $BaseUrl.Length - 3)
    }
    else {
        $BaseUrl.TrimEnd("/")
    }
    $healthUrl = "$root/api/tags"
    try {
        Invoke-RestMethod -Method Get -Uri $healthUrl -TimeoutSec 5 | Out-Null
    }
    catch {
        throw "Ollama API недоступен по адресу $healthUrl. Запустите 'ollama serve'."
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot

$oldEnv = @{
    OPENAI_API_KEY  = $env:OPENAI_API_KEY
    OPENAI_API_BASE = $env:OPENAI_API_BASE
    EMBED_API_BASE  = $env:EMBED_API_BASE
    LLM_MODEL       = $env:LLM_MODEL
    EMBED_MODEL     = $env:EMBED_MODEL
}

try {
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
        throw "Команда 'ollama' не найдена. Установите Ollama: https://ollama.com/download"
    }

    Ensure-OllamaReachable -BaseUrl $OllamaBaseUrl

    if (-not $SkipPull) {
        Write-Host "Pull LLM model: $LlmModel"
        & ollama pull $LlmModel
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

        Write-Host "Pull embed model: $EmbedModel"
        & ollama pull $EmbedModel
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    Set-Item Env:OPENAI_API_KEY "local"
    Set-Item Env:OPENAI_API_BASE $OllamaBaseUrl
    Set-Item Env:EMBED_API_BASE $OllamaBaseUrl
    Set-Item Env:LLM_MODEL $LlmModel
    Set-Item Env:EMBED_MODEL $EmbedModel

    # -m integration переопределяет дефолтный addopts (-m "not integration") из pytest.ini.
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
    foreach ($name in $oldEnv.Keys) {
        Set-EnvOrClear -Name $name -Value $oldEnv[$name]
    }
    Pop-Location
}
