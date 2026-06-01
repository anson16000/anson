@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "DELIVERY_DASHBOARD_CONFIG=%ROOT%\config\demo2019.yaml"

cd /d "%ROOT%"

echo.
echo ==============================
echo Delivery Dashboard - 2019 Demo
echo ==============================
echo Project: %ROOT%
echo Config: %DELIVERY_DASHBOARD_CONFIG%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\start_dashboard.ps1" -Root "%ROOT%" -Port 8090
if errorlevel 1 (
  echo.
  echo 2019 demo dashboard failed to start.
  echo Check logs: %ROOT%\logs\srv_err.log
  echo.
  pause
  exit /b 1
)

echo 2019 demo dashboard started successfully.
pause
