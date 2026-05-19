@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

cd /d "%ROOT%"

echo.
echo ==============================
echo Delivery Dashboard - Export Power BI Parquet
echo ==============================
echo Project: %ROOT%
echo.

call "%ROOT%\scripts\resolve_python.bat" "%ROOT%"
if errorlevel 1 (
  echo Python environment is not available.
  echo Please run 00-bootstrap-environment.bat or 00-init environment script first.
  echo.
  pause
  exit /b 1
)

echo Python: %PYTHON_EXE%
echo.

"%PYTHON_EXE%" "%ROOT%\main.py" export-powerbi
if errorlevel 1 (
  echo.
  echo Export failed. Please check the error message above.
  echo.
  pause
  exit /b 1
)

echo.
echo Export finished: %ROOT%\exports\powerbi_parquet
pause
