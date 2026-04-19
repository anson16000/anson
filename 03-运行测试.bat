@echo off
setlocal

set "ROOT=%~dp0"
set "LOG_FILE=%ROOT%logs\tests_last.log"

cd /d "%ROOT%"

echo.
echo ==============================
echo Delivery Dashboard - Tests
echo ==============================
echo Project: %ROOT%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = '%ROOT%';" ^
  "$logFile = '%LOG_FILE%';" ^
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
  "  if ($pythonCmd -and $pythonCmd.Source -notlike '*WindowsApps*') { $python = $pythonCmd.Source }" ^
  "}" ^
  "if (-not $python) {" ^
  "  Write-Host 'Python not found.';" ^
  "  Write-Host '1) Install Python 3.10+';" ^
  "  Write-Host '2) Ensure python is in PATH';" ^
  "  Write-Host '3) Or set env var DELIVERY_DASHBOARD_PYTHON to python.exe full path';" ^
  "  exit 1" ^
  "};" ^
  "if (-not (Test-Path (Split-Path $logFile -Parent))) { New-Item -ItemType Directory -Path (Split-Path $logFile -Parent) | Out-Null };" ^
  "Set-Content -Path $logFile -Value ('[' + (Get-Date) + '] Starting tests...');" ^
  "& $python -m unittest discover -s (Join-Path $root 'tests') -p 'test*.py' *>> $logFile;" ^
  "$exitCode = $LASTEXITCODE;" ^
  "Get-Content $logFile;" ^
  "exit $exitCode"

if errorlevel 1 (
  echo.
  echo Tests failed.
  echo Log file: %LOG_FILE%
  pause
  exit /b 1
)

echo.
echo Tests finished.
echo Log file: %LOG_FILE%
pause
