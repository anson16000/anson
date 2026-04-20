@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo.
echo ==============================
echo Delivery Dashboard - Bootstrap
echo ==============================
echo Project: %ROOT%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\bootstrap_env.ps1" -Root "%ROOT%"
if errorlevel 1 (
  echo.
  echo Bootstrap failed.
  echo Log file: %ROOT%logs\bootstrap_last.log
  pause
  exit /b 1
)

echo.
echo Bootstrap finished.
echo Log file: %ROOT%logs\bootstrap_last.log
pause
