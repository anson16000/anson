@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "DEMO_CONFIG=%ROOT%\config\demo2019.yaml"
set "DELIVERY_DASHBOARD_CONFIG=%DEMO_CONFIG%"
set "LOG_FILE=%ROOT%\logs\demo2019_import_last.log"

cd /d "%ROOT%"

echo.
echo ==============================
echo Delivery Dashboard - 2019 Demo Data
echo ==============================
echo Project: %ROOT%
echo Config: %DEMO_CONFIG%
echo.

where node >nul 2>nul
if errorlevel 1 (
  echo Node.js not found. Please install Node.js or run this script on the development computer.
  echo.
  pause
  exit /b 1
)

echo Generating synthetic 2019 demo source files...
node "%ROOT%\scripts\generate_demo_2019_data.mjs" "%ROOT%"
if errorlevel 1 (
  echo Failed to generate demo source files.
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

call "%ROOT%\scripts\resolve_python.bat" "%ROOT%"
if errorlevel 1 (
  echo Python not found. Running bootstrap first...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\bootstrap_env.ps1" -Root "%ROOT%"
  if errorlevel 1 (
    echo Bootstrap failed. Check logs\bootstrap_last.log.
    echo.
    pause
    exit /b 1
  )
  call "%ROOT%\scripts\resolve_python.bat" "%ROOT%"
)

if not defined PYTHON_EXE (
  echo Python not found after bootstrap.
  echo.
  pause
  exit /b 1
)

if not exist "%ROOT%\logs" mkdir "%ROOT%\logs"
echo Starting 2019 demo import... > "%LOG_FILE%"
"%PYTHON_EXE%" "%ROOT%\main.py" import --mode=force >> "%LOG_FILE%" 2>&1
set "IMPORT_EXIT=%ERRORLEVEL%"
type "%LOG_FILE%"

if not "%IMPORT_EXIT%"=="0" (
  echo.
  echo 2019 demo import failed.
  pause
  exit /b %IMPORT_EXIT%
)

echo.
echo 2019 demo data is ready.
echo Next: run 06-demo-2019-start.bat or 06-??2019????.bat
pause

