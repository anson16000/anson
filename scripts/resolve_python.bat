@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~1"
if not defined ROOT set "ROOT=%~dp0.."
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "PYTHON_EXE="

if defined DELIVERY_DASHBOARD_PYTHON (
  if exist "%DELIVERY_DASHBOARD_PYTHON%" set "PYTHON_EXE=%DELIVERY_DASHBOARD_PYTHON%"
)

if not defined PYTHON_EXE (
  if exist "%ROOT%\.venv\Scripts\python.exe" set "PYTHON_EXE=%ROOT%\.venv\Scripts\python.exe"
)

if not defined PYTHON_EXE (
  if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe"
  )
)

if not defined PYTHON_EXE (
  if exist "C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe"
  )
)

if not defined PYTHON_EXE (
  if exist "C:\Python312\python.exe" set "PYTHON_EXE=C:\Python312\python.exe"
)

if not defined PYTHON_EXE (
  for /f "delims=" %%P in ('where python 2^>nul') do (
    echo %%P | find /I "WindowsApps" >nul
    if errorlevel 1 (
      set "PYTHON_EXE=%%P"
      goto :resolved
    )
  )
)

:resolved
if not defined PYTHON_EXE (
  endlocal & exit /b 1
)

endlocal & set "PYTHON_EXE=%PYTHON_EXE%" & exit /b 0
