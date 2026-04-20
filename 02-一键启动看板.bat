@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "PORT=8090"
set "URL=http://127.0.0.1:%PORT%"
set "PYTHON_EXE="

cd /d "%ROOT%"

echo.
echo ==============================
echo Delivery Dashboard - Start
echo ==============================
echo Project: %ROOT%
echo URL: %URL%
echo.

call "%ROOT%\scripts\resolve_python.bat" "%ROOT%"
if errorlevel 1 (
  echo Python not found.
  echo Run 00-bootstrap-environment.bat first.
  echo.
  pause
  exit /b 1
)

echo Starting dashboard server...
start "Delivery Dashboard" /min "%PYTHON_EXE%" "%ROOT%\main.py" server --port %PORT%
timeout /t 5 /nobreak >nul
echo Opening browser...
start %URL%
echo.
echo Dashboard is starting. Check the browser for the dashboard.
echo.
pause
