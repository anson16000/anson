@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

cd /d "%ROOT%"

echo.
echo ==============================
echo Delivery Dashboard - Start
echo ==============================
echo Project: %ROOT%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\start_dashboard.ps1" -Root "%ROOT%" -Port 8090
if errorlevel 1 (
  echo.
  echo Dashboard failed to start.
  echo Check logs: %ROOT%\logs\srv_err.log
  echo.
  pause
  exit /b 1
)

echo Dashboard started successfully.
pause
