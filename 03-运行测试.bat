@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "LOG_FILE=%ROOT%\logs\tests_last.log"
set "PYTHON_EXE="

cd /d "%ROOT%"

echo.
echo ==============================
echo Delivery Dashboard - Tests
echo ==============================
echo Project: %ROOT%
echo.

call "%ROOT%\scripts\resolve_python.bat" "%ROOT%"
if errorlevel 1 (
  echo Python not found.
  echo Run 00-bootstrap-environment.bat first.
  echo.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$root = '%ROOT:&=\!%'; $logFile = '%LOG_FILE:&=\!%'; $python = '%PYTHON_EXE:&=\!%'; if (-not (Test-Path (Split-Path $logFile -Parent))) { New-Item -ItemType Directory -Path (Split-Path $logFile -Parent) | Out-Null }; Set-Content -Path $logFile -Value ('[' + (Get-Date) + '] Starting tests...'); & $python -m unittest discover -s (Join-Path $root 'tests') -p 'test*.py' *>> $logFile; $exitCode = $LASTEXITCODE; Get-Content $logFile; exit $exitCode"

if %errorlevel% neq 0 (
  echo.
  echo Tests failed.
  pause
  exit /b 1
)

echo.
echo Tests finished.
pause
