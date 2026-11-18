$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$engineDirectory = Join-Path $projectRoot "ai-engine"
$requirementsFile = Join-Path $engineDirectory "requirements.txt"
$localDataDirectory = if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    Join-Path $projectRoot "local-data"
} else {
    Join-Path $env:LOCALAPPDATA "LawSphere"
}
$pythonEnvironment = Join-Path $localDataDirectory "python-env"
$pythonExecutable = Join-Path $pythonEnvironment "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $requirementsFile -PathType Leaf)) {
    throw "Could not find backend requirements at $requirementsFile"
}

if (-not (Test-Path -LiteralPath $pythonExecutable -PathType Leaf)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $pythonCommand) {
        $supportedVersion = & $pythonCommand.Source -c "import sys; print(int(sys.version_info >= (3, 11)))"
        if ($LASTEXITCODE -ne 0 -or $supportedVersion.Trim() -ne "1") {
            $pythonCommand = $null
        }
    }

    if ($null -ne $pythonCommand) {
        & $pythonCommand.Source -m venv $pythonEnvironment
    } else {
        $pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
        if ($null -eq $pythonLauncher) {
            throw "Install Python 3.11 or later, then run this setup script again."
        }
        & $pythonLauncher.Source -3.11 -m venv $pythonEnvironment
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the Python virtual environment."
    }
}

& $pythonExecutable -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Could not update pip in the LawSphere virtual environment."
}

& $pythonExecutable -m pip install -r $requirementsFile
if ($LASTEXITCODE -ne 0) {
    throw "Could not install the LawSphere Python requirements. Check your connection and try again."
}

Write-Host "LawSphere Python dependencies are ready."
