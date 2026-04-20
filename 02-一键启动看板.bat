@echo off
setlocal

set "ROOT=%~dp0"
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
  "$port = %PORT%;" ^
  "$url = '%URL%';" ^
  "$python = '%PYTHON_EXE%';" ^
  "$inUse = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue;" ^
  "if ($inUse) {" ^
  "  Write-Host ('Port ' + $port + ' is already in use.');" ^
  "  exit 1" ^
  "};" ^
  "$serverScript = '& ''' + $python + ''' ''' + (Join-Path $root 'scripts\\run_server.py') + '''';" ^
  "Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $serverScript) -WorkingDirectory $root;" ^
  "Start-Sleep -Seconds 5;" ^
  "Start-Process $url;"

if errorlevel 1 (
  echo.
  pause
  exit /b 1
)

echo Dashboard server started.
echo.
pause
