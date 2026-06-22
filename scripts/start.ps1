[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RootDir = Split-Path -Parent $PSScriptRoot
$AiDir = Join-Path $RootDir "ai"
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$EnvPath = Join-Path $RootDir ".env"
$EnvExamplePath = Join-Path $RootDir ".env.example"
$VenvDir = Join-Path $AiDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$RequirementsPath = Join-Path $AiDir "requirements.txt"
$RequirementsStamp = Join-Path $VenvDir ".requirements.sha256"

function Write-Step([string]$Message) {
    Write-Host "[RMP] $Message" -ForegroundColor Cyan
}

function Get-EnvValue([string]$Name, [string]$DefaultValue = "") {
    $value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $DefaultValue
    }
    return $value
}

function Import-DotEnv {
    if (-not (Test-Path -LiteralPath $EnvPath)) {
        if (-not (Test-Path -LiteralPath $EnvExamplePath)) {
            throw ".env and .env.example are both missing."
        }
        Copy-Item -LiteralPath $EnvExamplePath -Destination $EnvPath
        Write-Step "Created .env from .env.example."
    }

    foreach ($line in Get-Content -LiteralPath $EnvPath) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }

        $parts = $trimmed.Split("=", 2)
        $name = $parts[0].Trim()
        if ([string]::IsNullOrWhiteSpace(
            [Environment]::GetEnvironmentVariable($name, "Process")
        )) {
            [Environment]::SetEnvironmentVariable($name, $parts[1].Trim(), "Process")
        }
    }
}

function Assert-Command([string]$Name, [string]$InstallHint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name was not found. $InstallHint"
    }
}

function Get-BasePython {
    $candidates = @(
        @{ File = "py"; Prefix = @("-3.13") },
        @{ File = "py"; Prefix = @("-3") },
        @{ File = "python"; Prefix = @() },
        @{ File = "python3"; Prefix = @() }
    )

    foreach ($candidate in $candidates) {
        if (-not (Get-Command $candidate.File -ErrorAction SilentlyContinue)) {
            continue
        }

        & $candidate.File @($candidate.Prefix) -c "import sys; print(sys.executable)" *> $null
        if ($LASTEXITCODE -eq 0) {
            return $candidate
        }
    }

    throw "Python 3 was not found. Install Python 3.11 or newer."
}

function Test-Venv {
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        return $false
    }

    & $VenvPython -c "import sys; assert sys.prefix != sys.base_prefix" *> $null
    return $LASTEXITCODE -eq 0
}

function Repair-Venv {
    if (Test-Venv) {
        return
    }

    if (Test-Path -LiteralPath $VenvDir) {
        Write-Step "Removing invalid or moved ai/.venv."
        Remove-Item -LiteralPath $VenvDir -Recurse -Force
    }

    $basePython = Get-BasePython
    Write-Step "Creating ai/.venv with $($basePython.File) $($basePython.Prefix -join ' ')."
    & $basePython.File @($basePython.Prefix) -m venv $VenvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Venv)) {
        throw "Failed to create a working AI virtual environment."
    }
}

function Install-AiDependencies {
    $currentHash = (Get-FileHash -LiteralPath $RequirementsPath -Algorithm SHA256).Hash
    $savedHash = if (Test-Path -LiteralPath $RequirementsStamp) {
        (Get-Content -LiteralPath $RequirementsStamp -Raw).Trim()
    } else {
        ""
    }

    if (-not $SkipInstall -and $currentHash -ne $savedHash) {
        Write-Step "Installing AI dependencies."
        & $VenvPython -m pip install -r $RequirementsPath
        if ($LASTEXITCODE -ne 0) {
            throw "AI dependency installation failed."
        }
        Set-Content -LiteralPath $RequirementsStamp -Value $currentHash -NoNewline
    }

    $providers = (Get-EnvValue "STT_PROVIDER_OPTIONS" "whisper").Split(",") |
        ForEach-Object { $_.Trim().ToLowerInvariant() } |
        Where-Object { $_ }

    $providerPackages = @{
        "whisper" = @{ Import = "whisper"; Package = "openai-whisper" }
        "faster_whisper" = @{ Import = "faster_whisper"; Package = "faster-whisper" }
        "whisperx" = @{ Import = "whisperx"; Package = "whisperx" }
    }

    foreach ($provider in $providers) {
        if (-not $providerPackages.ContainsKey($provider)) {
            throw "Unsupported STT provider in STT_PROVIDER_OPTIONS: $provider"
        }

        $moduleName = $providerPackages[$provider].Import
        & $VenvPython -c "import $moduleName" *> $null
        if ($LASTEXITCODE -ne 0) {
            if ($SkipInstall) {
                throw "Python module '$moduleName' is missing."
            }
            $packageName = $providerPackages[$provider].Package
            Write-Step "Installing STT provider package $packageName."
            & $VenvPython -m pip install $packageName
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to install STT provider package $packageName."
            }
        }
    }
}

function Install-NodeDependencies([string]$Directory, [string]$Label) {
    if (Test-Path -LiteralPath (Join-Path $Directory "node_modules")) {
        return
    }
    if ($SkipInstall) {
        throw "$Label node_modules is missing."
    }

    Write-Step "Installing $Label dependencies."
    Push-Location $Directory
    try {
        & npm.cmd install
        if ($LASTEXITCODE -ne 0) {
            throw "$Label dependency installation failed."
        }
    } finally {
        Pop-Location
    }
}

function Assert-PortAvailable([int]$Port, [string]$ServiceName) {
    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listeners) {
        $pids = ($listeners | Select-Object -ExpandProperty OwningProcess -Unique) -join ", "
        throw "$ServiceName port $Port is already in use by PID(s): $pids"
    }
}

function Start-ServiceProcess(
    [string]$Name,
    [string]$FilePath,
    [string[]]$ArgumentList,
    [string]$WorkingDirectory
) {
    Write-Step "Starting $Name."
    return Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -NoNewWindow `
        -PassThru
}

function Stop-ProcessTree([System.Diagnostics.Process]$Process) {
    if ($Process.HasExited) {
        return
    }

    & taskkill.exe /PID $Process.Id /T /F *> $null
}

Import-DotEnv
Assert-Command "node" "Install the current Node.js LTS release."
Assert-Command "npm.cmd" "Reinstall Node.js with npm."
Assert-Command (Get-EnvValue "FFMPEG_BINARY" "ffmpeg") "Install ffmpeg and add it to PATH."
Assert-Command (Get-EnvValue "FFPROBE_BINARY" "ffprobe") "Install ffprobe and add it to PATH."

Repair-Venv
Install-AiDependencies
Install-NodeDependencies $BackendDir "Backend"
Install-NodeDependencies $FrontendDir "Frontend"

$CudaAvailable = (& $VenvPython -c "import torch; print('1' if torch.cuda.is_available() else '0')").Trim()
if ($CudaAvailable -eq "1") {
    [Environment]::SetEnvironmentVariable("STT_DEVICE_OPTIONS", "cpu,cuda", "Process")
} else {
    [Environment]::SetEnvironmentVariable("STT_DEVICE_OPTIONS", "cpu", "Process")
    if ((Get-EnvValue "WHISPER_DEVICE" "cpu") -eq "cuda") {
        Write-Warning "CUDA is unavailable. Falling back to WHISPER_DEVICE=cpu and int8."
        [Environment]::SetEnvironmentVariable("WHISPER_DEVICE", "cpu", "Process")
        [Environment]::SetEnvironmentVariable("WHISPER_COMPUTE_TYPE", "int8", "Process")
    }
}

$AiPort = [int](Get-EnvValue "AI_PORT" "8000")
$BackendPort = [int](Get-EnvValue "BACKEND_PORT" "3000")
$FrontendPort = [int](Get-EnvValue "FRONTEND_PORT" "5173")

Assert-PortAvailable $AiPort "AI"
Assert-PortAvailable $BackendPort "Backend"
Assert-PortAvailable $FrontendPort "Frontend"

Push-Location $AiDir
try {
    & $VenvPython -c "import fastapi, uvicorn; import app.main" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "AI application import check failed."
    }
} finally {
    Pop-Location
}

Write-Step "Environment check completed."
if ($CheckOnly) {
    Write-Host "AI:       http://127.0.0.1:$AiPort"
    Write-Host "Backend:  http://127.0.0.1:$BackendPort"
    Write-Host "Frontend: http://127.0.0.1:$FrontendPort"
    exit 0
}

$processes = @()
try {
    $processes += Start-ServiceProcess "AI" $VenvPython @(
        "-m", "uvicorn", "app.main:app",
        "--host", (Get-EnvValue "AI_HOST" "127.0.0.1"),
        "--port", "$AiPort"
    ) $AiDir
    $processes += Start-ServiceProcess "Backend" "npm.cmd" @("start") $BackendDir
    $processes += Start-ServiceProcess "Frontend" "npm.cmd" @(
        "run", "dev", "--",
        "--host", "127.0.0.1",
        "--port", "$FrontendPort",
        "--strictPort"
    ) $FrontendDir

    Write-Host ""
    Write-Host "Frontend: http://127.0.0.1:$FrontendPort" -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop all services."

    while ($true) {
        Start-Sleep -Seconds 1
        $exited = $processes | Where-Object { $_.HasExited }
        if ($exited) {
            $names = ($exited | ForEach-Object { $_.Id }) -join ", "
            throw "A service process exited unexpectedly. PID(s): $names"
        }
    }
} finally {
    Write-Step "Stopping all services."
    foreach ($process in $processes) {
        Stop-ProcessTree $process
    }
}
