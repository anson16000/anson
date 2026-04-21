@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~1"
if not defined ROOT set "ROOT=%~dp0.."
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "PYTHON_EXE="

if defined DELIVERY_DASHBOARD_PYTHON (
  call :try_candidate "%DELIVERY_DASHBOARD_PYTHON%"
  if defined PYTHON_EXE goto resolved
)

call :try_candidate "%ROOT%\.venv\Scripts\python.exe"
if defined PYTHON_EXE goto resolved

call :try_candidate "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe"
if defined PYTHON_EXE goto resolved

call :try_candidate "C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe"
if defined PYTHON_EXE goto resolved

call :try_candidate "C:\Python312\python.exe"
if defined PYTHON_EXE goto resolved

if not defined PYTHON_EXE (
  for /f "delims=" %%P in ('where python 2^>nul') do (
    echo %%P | find /I "WindowsApps" >nul
    if errorlevel 1 (
      call :try_candidate "%%P"
      if defined PYTHON_EXE goto resolved
    )
  )
)

:resolved
if not defined PYTHON_EXE (
  endlocal & exit /b 1
)

endlocal & set "PYTHON_EXE=%PYTHON_EXE%" & exit /b 0

:try_candidate
set "CANDIDATE=%~1"
if not defined CANDIDATE goto :eof
if not exist "%CANDIDATE%" goto :eof
"%CANDIDATE%" -c "import sys" >nul 2>&1
if errorlevel 1 goto :eof
set "PYTHON_EXE=%CANDIDATE%"
goto :eof
