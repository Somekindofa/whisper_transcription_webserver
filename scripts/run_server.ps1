<#
Run the server with HOST/PORT environment variables set and redirect logs.
Usage (recommended from Scheduled Task):
  powershell -ExecutionPolicy Bypass -File C:\path\to\run_server.ps1 -PythonExe "C:\Python\python.exe" -BindHost 0.0.0.0 -Port 8000 -WorkingDir "C:\path\to\whisper_transcriptor"

If -PythonExe is omitted the script will try to find `python` on PATH.
#>
param(
    [string]$PythonExe = "",
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 8000,
    [string]$WorkingDir = $(Split-Path -Parent $MyInvocation.MyCommand.Definition)
)

Set-StrictMode -Version Latest

if (-not $PythonExe) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) { $PythonExe = $pythonCmd.Source }
}

if (-not (Test-Path $PythonExe)) {
    Write-Error "python executable not found. Pass -PythonExe 'C:\path\to\python.exe' or ensure python is on PATH."
    exit 1
}

# Ensure working dir is absolute
$WorkingDir = (Resolve-Path -Path $WorkingDir).Path

# Set env vars for the child process
$env:HOST = $BindHost
$env:PORT = "$Port"

# Ensure log path exists
$logDir = Join-Path $WorkingDir "storage"
if (-not (Test-Path $logDir)) { New-Item -Path $logDir -ItemType Directory -Force | Out-Null }
$outLog = Join-Path $logDir "server.out.log"
$errLog = Join-Path $logDir "server.err.log"

# Path to app.py
$app = Join-Path $WorkingDir "app.py"
if (-not (Test-Path $app)) { Write-Error "app.py not found at $app"; exit 1 }

# Start detached background process and redirect stdout/stderr to separate files
Start-Process -FilePath $PythonExe -ArgumentList "`"$app`"" -WorkingDirectory $WorkingDir -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog

Write-Output "Started Whisper Transcriptor via: $PythonExe $app`nLogs -> $outLog (stdout)  $errLog (stderr)"