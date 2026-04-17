@echo off
setlocal

set "ROOT=%~dp0"
set "PORT=8090"
set "URL=http://127.0.0.1:%PORT%"

cd /d "%ROOT%"

echo.
echo ==============================
echo Delivery Dashboard - Start
echo ==============================
echo Project: %ROOT%
echo URL: %URL%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = '%ROOT%';" ^
  "$port = %PORT%;" ^
  "$url = '%URL%';" ^
  "$python = $env:DELIVERY_DASHBOARD_PYTHON;" ^
  "if ($python -and -not (Test-Path $python)) { $python = $null };" ^
  "if (-not $python) {" ^
  "  $candidates = @(" ^
  "    'C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe'," ^
  "    ('C:\Users\' + $env:USERNAME + '\AppData\Local\Programs\Python\Python312\python.exe')," ^
  "    'C:\Python312\python.exe'" ^
  "  );" ^
  "  foreach ($candidate in $candidates) {" ^
  "    if ($candidate -and (Test-Path $candidate)) { $python = $candidate; break }" ^
  "  }" ^
  "}" ^
  "if (-not $python) {" ^
  "  $pythonCmd = Get-Command python -ErrorAction SilentlyContinue;" ^
  "  if ($pythonCmd) { $python = $pythonCmd.Source }" ^
  "}" ^
  "if (-not $python) {" ^
  "  Write-Host 'Python not found.';" ^
  "  Write-Host '1) Install Python 3.10+';" ^
  "  Write-Host '2) Ensure python is in PATH';" ^
  "  Write-Host '3) Or set env var DELIVERY_DASHBOARD_PYTHON to python.exe full path';" ^
  "  exit 1" ^
  "};" ^
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
