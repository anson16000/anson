@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "PYTHON_EXE="
set "LOG_FILE=%ROOT%\logs\import_last.log"
set "IMPORT_MODE=auto"

cd /d "%ROOT%"

echo.
echo ==============================
echo Delivery Dashboard - Import
echo ==============================
echo Project: %ROOT%
echo Mode: %IMPORT_MODE%
echo.

call "%ROOT%\scripts\resolve_python.bat" "%ROOT%"
if errorlevel 1 (
  echo Python not found.
  echo Run 00-bootstrap-environment.bat first.
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
  echo Stopping dashboard ^(PID=%DASH_PID%^)
  taskkill /PID %DASH_PID% /F >nul 2>&1
  timeout /t 1 /nobreak >nul
)

if not exist "%ROOT%\logs" mkdir "%ROOT%\logs"
echo Starting import... > "%LOG_FILE%"
"%PYTHON_EXE%" "%ROOT%\main.py" import --mode=%IMPORT_MODE% >> "%LOG_FILE%" 2>&1
type "%LOG_FILE%"

if %errorlevel% neq 0 (
  echo.
  echo Import failed.
  pause
  exit /b %errorlevel%
)

echo Import finished.
pause
