@echo off
setlocal

set "MODE=%~1"
set "TARGET_AGENT=%~2"
set "PACKAGE_ID=%~3"
set "FORCE_FLAG=%~4"

if "%MODE%"=="" set "MODE=dry-run"
if "%TARGET_AGENT%"=="" set "TARGET_AGENT=codex"

set "SCRIPT_DIR=%~dp0"
set "PS1=%SCRIPT_DIR%run_start_workflow_e2e.ps1"

if not exist "%PS1%" (
  echo ERROR: launcher not found: "%PS1%"
  exit /b 1
)

set "CMD=powershell -ExecutionPolicy Bypass -File "%PS1%" -Mode %MODE% -TargetAgent %TARGET_AGENT%"

if not "%PACKAGE_ID%"=="" (
  set "CMD=%CMD% -PackageId %PACKAGE_ID%"
)

if /I "%FORCE_FLAG%"=="force" (
  set "CMD=%CMD% -Force"
)

echo Running: %CMD%
call %CMD%
exit /b %ERRORLEVEL%
