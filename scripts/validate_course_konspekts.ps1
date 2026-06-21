param(
    [string]$Course = "",
    [string]$CourseDir = "",
    [switch]$AllCourses,
    [string]$Filter = "*.md",
    [ValidateSet("cloud", "local")]
    [string]$Profile = "cloud",
    [string[]]$ExcludeCourse = @(".obsidian", "graph_generations", "ml", "offline_quiz_cache", "sessions"),
    [switch]$NoExpectSourceSha,
    [switch]$ExpectPresentation,
    [switch]$ExpectPresentationSha,
    [switch]$AllowDirectYouTube,
    [switch]$NoStrict
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom
$env:PYTHONIOENCODING = "utf-8"

function Resolve-ValidationTargets {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$DataRoot,
        [string]$Course,
        [string]$CourseDir,
        [bool]$AllCourses,
        [string[]]$ExcludeCourse
    )

    if ($AllCourses) {
        return @(Get-ChildItem -LiteralPath $DataRoot -Directory |
            Where-Object { $ExcludeCourse -notcontains $_.Name } |
            Sort-Object FullName |
            ForEach-Object { $_.FullName })
    }

    if (-not [string]::IsNullOrWhiteSpace($CourseDir)) {
        if ([System.IO.Path]::IsPathRooted($CourseDir)) {
            return @($CourseDir)
        }
        return @(Join-Path $RepoRoot $CourseDir)
    }

    if (-not [string]::IsNullOrWhiteSpace($Course)) {
        return @(Join-Path $DataRoot $Course)
    }

    Write-Error "Specify -Course <name>, -CourseDir <path>, or -AllCourses."
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$dataRoot = Join-Path $repoRoot "data"
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$validatorScript = Join-Path $repoRoot "scripts\validate_smart_konspekt.py"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Error "Project interpreter not found: $pythonExe"
}

if (-not (Test-Path -LiteralPath $validatorScript)) {
    Write-Error "Validator script not found: $validatorScript"
}

if (-not (Test-Path -LiteralPath $dataRoot)) {
    Write-Error "Data directory not found: $dataRoot"
}

$targets = @(Resolve-ValidationTargets `
    -RepoRoot $repoRoot `
    -DataRoot $dataRoot `
    -Course $Course `
    -CourseDir $CourseDir `
    -AllCourses $AllCourses.IsPresent `
    -ExcludeCourse $ExcludeCourse)

$allFiles = @()
foreach ($target in $targets) {
    if (-not (Test-Path -LiteralPath $target)) {
        Write-Error "Course directory not found: $target"
    }
    $courseFiles = @(Get-ChildItem -LiteralPath $target -Recurse -File -Filter $Filter | Sort-Object FullName)
    foreach ($file in $courseFiles) {
        $allFiles += $file
    }
}

if ($allFiles.Count -eq 0) {
    Write-Host "No files matched '$Filter'."
    exit 0
}

Write-Host "Data root: $dataRoot"
Write-Host "Targets: $($targets.Count)"
foreach ($target in $targets) {
    Write-Host " - $target"
}
Write-Host "Matched files: $($allFiles.Count)"
Write-Host "Profile: $Profile"
Write-Host ""

$failed = @()

foreach ($file in $allFiles) {
    Write-Host "== Validate: $($file.FullName) =="

    $arguments = @(
        $validatorScript,
        $file.FullName,
        "--profile",
        $Profile
    )

    if (-not $NoExpectSourceSha.IsPresent) {
        $arguments += "--expect-source-sha"
    }

    if ($ExpectPresentation.IsPresent) {
        $arguments += "--expect-presentation"
    }

    if ($ExpectPresentationSha.IsPresent) {
        $arguments += "--expect-presentation-sha"
    }

    if ($AllowDirectYouTube.IsPresent) {
        $arguments += "--allow-direct-youtube"
    }

    if (-not $NoStrict.IsPresent) {
        $arguments += "--strict"
    }

    & $pythonExe @arguments
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        $failed += $file.FullName
    }

    Write-Host ""
}

Write-Host "== Summary =="
Write-Host "Targets: $($targets.Count)"
Write-Host "Checked: $($allFiles.Count)"
Write-Host "Failed: $($failed.Count)"

if ($failed.Count -gt 0) {
    foreach ($path in $failed) {
        Write-Host "FAIL: $path"
    }
    exit 1
}

Write-Host "All smart konspekts passed."
exit 0
