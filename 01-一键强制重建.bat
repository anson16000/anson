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

if defined DELIVERY_DASHBOARD_PYTHON (
  if exist "%DELIVERY_DASHBOARD_PYTHON%" set "PYTHON_EXE=%DELIVERY_DASHBOARD_PYTHON%"
)
if exist "C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe" (
  set "PYTHON_EXE=C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe"
)
if not defined PYTHON_EXE (
  if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe"
  )
)
if not defined PYTHON_EXE (
  if exist "C:\Python312\python.exe" set "PYTHON_EXE=C:\Python312\python.exe"
)
if not defined PYTHON_EXE (
  for %%P in (python.exe) do (
    if not "%%~$PATH:P"=="" set "PYTHON_EXE=python"
  )
)
if not defined PYTHON_EXE (
  echo Python not found.
  echo 1^) Install Python 3.10+
  echo 2^) Ensure python is in PATH
  echo 3^) Or set env var DELIVERY_DASHBOARD_PYTHON to python.exe full path
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
