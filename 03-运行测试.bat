@echo off
setlocal

set "ROOT=%~dp0"
set "LOG_FILE=%ROOT%logs\tests_last.log"
set "PYTHON_EXE="

cd /d "%ROOT%"

echo.
echo ==============================
echo Delivery Dashboard - Tests
echo ==============================
echo Project: %ROOT%
echo.

call "%ROOT%scripts\resolve_python.bat" "%ROOT%"
if errorlevel 1 (
  echo Python not found.
  echo 1^) Run 00-bootstrap-environment.bat or 00-初始化环境.bat
  echo 2^) Or install Python 3.12 and create the project .venv
  echo 3^) Or set env var DELIVERY_DASHBOARD_PYTHON to a valid python.exe path
  echo.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = '%ROOT%';" ^
  "$logFile = '%LOG_FILE%';" ^
  "$python = '%PYTHON_EXE%';" ^
  "if (-not (Test-Path (Split-Path $logFile -Parent))) { New-Item -ItemType Directory -Path (Split-Path $logFile -Parent) | Out-Null };" ^
  "Set-Content -Path $logFile -Value ('[' + (Get-Date) + '] Starting tests...');" ^
  "& $python -m unittest discover -s (Join-Path $root 'tests') -p 'test*.py' *>> $logFile;" ^
  "$exitCode = $LASTEXITCODE;" ^
  "Get-Content $logFile;" ^
  "exit $exitCode"

if errorlevel 1 (
  echo.
  echo Tests failed.
  echo Log file: %LOG_FILE%
  pause
  exit /b 1
)

echo.
echo Tests finished.
echo Log file: %LOG_FILE%
pause
