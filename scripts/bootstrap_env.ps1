param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )

    $line = "[{0}] [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    Write-Host $line
    if ($script:LogFile) {
        Add-Content -Path $script:LogFile -Value $line -Encoding UTF8
    }
}

function Fail-Step {
    param([string]$Message)
    Write-Log -Message $Message -Level "ERROR"
    throw $Message
}

function Ensure-Directory {
    param([string]$PathValue)
    if (-not (Test-Path -LiteralPath $PathValue)) {
        New-Item -ItemType Directory -Path $PathValue -Force | Out-Null
        Write-Log "Created directory: $PathValue"
    } else {
        Write-Log "Directory exists: $PathValue"
    }
}

function Test-Network {
    try {
        $result = Test-NetConnection -ComputerName "www.python.org" -Port 443 -WarningAction SilentlyContinue
        return [bool]$result.TcpTestSucceeded
    } catch {
        return $false
    }
}

function Get-PythonVersion {
    param([string]$PythonPath)

    try {
        $version = & $PythonPath -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null
        if (-not $version) {
            return $null
        }
        return [version]($version.Trim())
    } catch {
        return $null
    }
}

function Resolve-Python {
    param([string]$ProjectRoot)

    $candidates = New-Object System.Collections.Generic.List[string]

    if ($env:DELIVERY_DASHBOARD_PYTHON) {
        $candidates.Add($env:DELIVERY_DASHBOARD_PYTHON)
    }

    $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) {
        $candidates.Add($venvPython)
    }

    foreach ($candidate in @(
        "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python312\python.exe",
        "C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe",
        "C:\Python312\python.exe"
    )) {
        if (Test-Path -LiteralPath $candidate) {
            $candidates.Add($candidate)
        }
    }

    try {
        $pythonCommands = Get-Command python -ErrorAction SilentlyContinue -All
        foreach ($command in $pythonCommands) {
            if ($command.Source -and $command.Source -notlike "*WindowsApps*") {
                $candidates.Add($command.Source)
            }
        }
    } catch {
        # ignore PATH lookup failures
    }

    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (-not (Test-Path -LiteralPath $candidate)) {
            continue
        }
        $version = Get-PythonVersion -PythonPath $candidate
        if ($version -and $version -ge [version]"3.12.0") {
            return @{
                Path = $candidate
                Version = $version.ToString()
            }
        }
        if ($candidate -match "Python312\\python\.exe$") {
            return @{
                Path = $candidate
                Version = "3.12.x"
            }
        }
    }

    return $null
}

function Install-Python312 {
    param([string]$ProjectRoot)

    if (-not (Test-Network)) {
        Fail-Step "Network is unavailable. Please connect to the internet or install Python 3.12 manually."
    }

    $tempDir = Join-Path $env:TEMP "delivery-dashboard-bootstrap"
    Ensure-Directory $tempDir
    $installerPath = Join-Path $tempDir "python-3.12-amd64.exe"
    $urls = @(
        "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe",
        "https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe",
        "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    )

    $downloaded = $false
    foreach ($url in $urls) {
        try {
            Write-Log "Downloading Python installer: $url"
            Invoke-WebRequest -Uri $url -OutFile $installerPath -UseBasicParsing
            $downloaded = $true
            break
        } catch {
            Write-Log "Download failed: $url" "WARN"
        }
    }

    if (-not $downloaded) {
        Fail-Step "Failed to download Python installer. Please install Python 3.12 manually from https://www.python.org/downloads/windows/"
    }

    Write-Log "Installing Python 3.12 silently"
    $process = Start-Process -FilePath $installerPath -ArgumentList @(
        "/quiet",
        "InstallAllUsers=0",
        "PrependPath=1",
        "Include_test=0",
        "Include_launcher=1",
        "Include_pip=1",
        "SimpleInstall=1"
    ) -Wait -PassThru

    if ($process.ExitCode -ne 0) {
        Fail-Step "Python installation failed with exit code $($process.ExitCode)."
    }

    Start-Sleep -Seconds 3
    $resolved = Resolve-Python -ProjectRoot $ProjectRoot
    if (-not $resolved) {
        Fail-Step "Python 3.12 was installed, but no usable interpreter could be found afterwards."
    }

    Write-Log "Python installed successfully: $($resolved.Path)"
    return $resolved
}

$Root = (Resolve-Path $Root).Path
$logsDir = Join-Path $Root "logs"
Ensure-Directory $logsDir
$script:LogFile = Join-Path $logsDir "bootstrap_last.log"
Set-Content -Path $script:LogFile -Value ("[{0}] [INFO] Starting bootstrap..." -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")) -Encoding UTF8

try {
    Write-Log "Project root: $Root"

    foreach ($file in @(
        (Join-Path $Root "requirements.txt"),
        (Join-Path $Root "main.py"),
        (Join-Path $Root "config\config.yaml")
    )) {
        if (-not (Test-Path -LiteralPath $file)) {
            Fail-Step "Missing required file: $file"
        }
        Write-Log "Required file found: $file"
    }

    foreach ($dir in @(
        "data",
        "db",
        "logs",
        "data\orders_raw",
        "data\orders_stage",
        "data\orders",
        "data\riders",
        "data\merchants",
        "data\partners"
    )) {
        Ensure-Directory (Join-Path $Root $dir)
    }

    $dbPath = Join-Path $Root "db\delivery_analysis.duckdb"
    if (Test-Path -LiteralPath $dbPath) {
        Write-Log "Database file exists: $dbPath"
    } else {
        Write-Log "Database file does not exist yet. It will be created after data import."
    }

    $portInUse = $false
    try {
        $portInUse = [bool](Get-NetTCPConnection -LocalPort 8090 -State Listen -ErrorAction SilentlyContinue)
    } catch {
        $portInUse = $false
    }
    if ($portInUse) {
        Write-Log "Port 8090 is already in use. Please confirm whether an existing dashboard process should be stopped first." "WARN"
    } else {
        Write-Log "Port 8090 is available."
    }

    $python = Resolve-Python -ProjectRoot $Root
    if ($python) {
        Write-Log "Detected usable Python: $($python.Path) ($($python.Version))"
    } else {
        Write-Log "Python 3.12 was not found. Starting automatic installation."
        $python = Install-Python312 -ProjectRoot $Root
    }

    $venvPath = Join-Path $Root ".venv"
    $venvPython = Join-Path $venvPath "Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $venvPython)) {
        Write-Log "Creating project virtual environment: $venvPath"
        & $python.Path -m venv $venvPath
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $venvPython)) {
            Fail-Step "Failed to create virtual environment at $venvPath"
        }
    } else {
        Write-Log "Reusing virtual environment: $venvPath"
    }

    Write-Log "Upgrading pip / setuptools / wheel"
    & $venvPython -m pip install --upgrade pip setuptools wheel
    if ($LASTEXITCODE -ne 0) {
        Fail-Step "Failed to upgrade pip tooling."
    }

    Write-Log "Installing requirements.txt"
    & $venvPython -m pip install -r (Join-Path $Root "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        Fail-Step "Failed to install project dependencies."
    }

    Write-Log "Validating core Python imports"
    & $venvPython -c "import fastapi, sqlalchemy, duckdb, pandas, openpyxl, uvicorn"
    if ($LASTEXITCODE -ne 0) {
        Fail-Step "Dependency validation failed."
    }

    $env:DELIVERY_DASHBOARD_PYTHON = $venvPython
    setx DELIVERY_DASHBOARD_PYTHON $venvPython | Out-Null
    Write-Log "Persisted DELIVERY_DASHBOARD_PYTHON=$venvPython"

    Write-Log "Bootstrap completed successfully."
    Write-Log "Next steps:"
    Write-Log "1. Run the dashboard start script in the project root."
    Write-Log "2. If needed, run the normal import script."
    Write-Log "3. If needed, run the force rebuild script."
    Write-Log "4. If needed, run the test script."
    exit 0
} catch {
    Write-Log ("Bootstrap failed: {0}" -f $_.Exception.Message) "ERROR"
    Write-Host ""
    Write-Host "Bootstrap failed."
    Write-Host "Log file: $script:LogFile"
    Write-Host "Please review the log and retry."
    exit 1
}
