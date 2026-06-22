$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot
$EnvPath = Join-Path $RootDir ".env"
$values = @{}

if (Test-Path -LiteralPath $EnvPath) {
    foreach ($line in Get-Content -LiteralPath $EnvPath) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }
        $parts = $trimmed.Split("=", 2)
        $values[$parts[0].Trim()] = $parts[1].Trim()
    }
}

function Get-PortValue([string]$Name, [int]$DefaultValue) {
    if ($values.ContainsKey($Name) -and $values[$Name]) {
        return [int]$values[$Name]
    }
    return $DefaultValue
}

$ports = @(
    Get-PortValue "FRONTEND_PORT" 5173
    Get-PortValue "BACKEND_PORT" 3000
    Get-PortValue "AI_PORT" 8000
)
$listeners = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -in $ports }

if (-not $listeners) {
    Write-Host "[RMP] No RMP service ports are listening."
    exit 0
}

foreach ($processId in ($listeners | Select-Object -ExpandProperty OwningProcess -Unique)) {
    Write-Host "[RMP] Stopping process tree $processId."
    & taskkill.exe /PID $processId /T /F *> $null
}
