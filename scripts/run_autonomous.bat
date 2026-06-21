@echo off
setlocal
set "repoRoot=%~dp0.."
set "pythonExe=%repoRoot%\.venv\Scripts\python.exe"

if not exist "%pythonExe%" (
    set "pythonExe=python"
)

set "agent=%~1"
if "%agent%"=="" set "agent=cursor_ai"

set "pkg=%~2"

echo Running autonomous loop...
if "%pkg%"=="" (
    "%pythonExe%" "%repoRoot%\scripts\run_autonomous.py" --agent "%agent%"
) else (
    "%pythonExe%" "%repoRoot%\scripts\run_autonomous.py" --agent "%agent%" --package "%pkg%"
)

exit /b %ERRORLEVEL%
