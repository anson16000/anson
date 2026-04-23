param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [int]$Port = 8090
)

$ErrorActionPreference = "Stop"

function Write-Info {
    param([string]$Message)
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message)
}

function Test-PythonExecutable {
    param([string]$PythonPath)
    if (-not $PythonPath -or -not (Test-Path -LiteralPath $PythonPath)) {
        return $false
    }
    try {
        & $PythonPath -c "import sys" 1>$null 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Resolve-PythonPath {
    param([string]$ProjectRoot)

    $candidates = @(
        $env:DELIVERY_DASHBOARD_PYTHON,
        (Join-Path $ProjectRoot ".venv\Scripts\python.exe"),
        "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python312\python.exe",
        "C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe",
        "C:\Python312\python.exe"
    ) | Where-Object { $_ }

    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (Test-PythonExecutable -PythonPath $candidate) {
            return $candidate
        }
    }

    return $null
}

function Stop-TrackedProcess {
    param([string]$PidFile)

    if (-not (Test-Path -LiteralPath $PidFile)) {
        return
    }

    $pidText = (Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if (-not $pidText) {
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
        return
    }

    $oldProcess = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
    if ($oldProcess) {
        Write-Info "Stopping previous dashboard process PID=$pidText"
        Stop-Process -Id $oldProcess.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }

    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
}

function Test-HttpReady {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
    } catch {
        return $false
    }
}

$Root = $Root.Trim('"', "'").TrimEnd('\', '/')
$Root = (Resolve-Path -LiteralPath $Root).Path
$logsDir = Join-Path $Root "logs"
$pidFile = Join-Path $logsDir "dashboard_server.pid"
$stdoutLog = Join-Path $logsDir "srv_out.log"
$stderrLog = Join-Path $logsDir "srv_err.log"
$url = "http://127.0.0.1:$Port"
$healthUrl = "$url/api/v1/meta"

if (-not (Test-Path -LiteralPath $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

Set-Content -LiteralPath $stdoutLog -Value "" -Encoding UTF8
Set-Content -LiteralPath $stderrLog -Value "" -Encoding UTF8

Write-Info "Checking Python environment"
$pythonExe = Resolve-PythonPath -ProjectRoot $Root
if (-not $pythonExe) {
    Write-Info "Python environment is unavailable. Running bootstrap."
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "scripts\bootstrap_env.ps1") -Root $Root
    if ($LASTEXITCODE -ne 0) {
        throw "Bootstrap failed. See logs\bootstrap_last.log for details."
    }
    $pythonExe = Resolve-PythonPath -ProjectRoot $Root
}

if (-not $pythonExe) {
    throw "No usable Python interpreter was found after bootstrap."
}

Write-Info "Using Python: $pythonExe"

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    Write-Info "Port $Port is already listening. Opening browser."
    Start-Process $url | Out-Null
    exit 0
}

Stop-TrackedProcess -PidFile $pidFile

$serverScript = Join-Path $Root "main.py"
Write-Info "Starting dashboard server"
$process = Start-Process `
    -FilePath $pythonExe `
    -ArgumentList @($serverScript, "server", "--port", "$Port") `
    -WorkingDirectory $Root `
    -WindowStyle Minimized `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -PassThru

Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ASCII

$deadline = (Get-Date).AddSeconds(35)
while ((Get-Date) -lt $deadline) {
    if ($process.HasExited) {
        break
    }
    if (Test-HttpReady -Url $healthUrl) {
        Write-Info "Dashboard is ready: $url"
        Start-Process $url | Out-Null
        exit 0
    }
    Start-Sleep -Seconds 1
    $process.Refresh()
}

$process.Refresh()
if (-not $process.HasExited -and (Test-HttpReady -Url $healthUrl)) {
    Write-Info "Dashboard is ready: $url"
    Start-Process $url | Out-Null
    exit 0
}

if ($process.HasExited) {
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

$errorTail = ""
if (Test-Path -LiteralPath $stderrLog) {
    $errorTail = (Get-Content -LiteralPath $stderrLog -Tail 40 -ErrorAction SilentlyContinue) -join [Environment]::NewLine
}

if ($errorTail) {
    throw "Dashboard failed to start.`n`n$errorTail"
}

throw "Dashboard failed to start within 35 seconds. Check logs\srv_out.log and logs\srv_err.log."
