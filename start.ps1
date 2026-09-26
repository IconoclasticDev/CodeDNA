param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot

$bundledPython = "C:\Users\as030\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (Test-Path -LiteralPath $bundledPython) {
    $pythonExecutable = $bundledPython
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python 3.11 or newer is required. Install Python or update the bundled runtime path in start.ps1."
    }
    $pythonExecutable = $pythonCommand.Source
}

$env:CODEDNA_PORT = $Port.ToString()
Write-Host "Starting CodeDNA at http://127.0.0.1:$Port"
& $pythonExecutable -m codedna.server

