@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON_EXE="
set "LOG_FILE=%ROOT%logs\force_rebuild_last.log"
set "IMPORT_MODE=force"

cd /d "%ROOT%"

echo.
echo ==============================
echo Delivery Dashboard - Force Rebuild
echo ==============================
echo Project: %ROOT%
echo Mode: %IMPORT_MODE%
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

set "DASH_PID="
for /f "tokens=5" %%I in ('netstat -ano ^| findstr /R /C:":8090 .*LISTENING"') do (
  set "DASH_PID=%%I"
  goto :found_dashboard_pid
)

:found_dashboard_pid
if defined DASH_PID (
  echo Dashboard is running ^(PID=%DASH_PID%^), stopping it before import...
  taskkill /PID %DASH_PID% /F >nul 2>&1
  timeout /t 1 /nobreak >nul
)

if not exist "%ROOT%logs" mkdir "%ROOT%logs"
echo [%date% %time%] Starting import... > "%LOG_FILE%"
echo Mode: %IMPORT_MODE% >> "%LOG_FILE%"
"%PYTHON_EXE%" "%ROOT%main.py" import --mode=%IMPORT_MODE% >> "%LOG_FILE%" 2>&1
type "%LOG_FILE%"
if %errorlevel% neq 0 (
  echo.
  echo Force rebuild failed. ExitCode=%errorlevel%
  echo Log file: %LOG_FILE%
  pause
  exit /b %errorlevel%
)

echo.
echo Force rebuild finished.
echo Log file: %LOG_FILE%
pause
