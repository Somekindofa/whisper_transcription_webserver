<#
Create a scheduled task that runs the server at system startup (runs as SYSTEM).
Requires: Administrator privileges.

Usage (Admin PowerShell):
  .\install-windows-schtask.ps1 -PythonExe "C:\Python\python.exe" -Host 0.0.0.0 -Port 8000 -TaskName "WhisperTranscriptor"

This will:
  - create a task that runs at system startup
  - start run_server.ps1 which launches `python app.py`
  - add a Windows Firewall rule for the selected PORT (optional)
#>
param(
    [string]$PythonExe = "",
    [string]$Host = "0.0.0.0",
    [int]$Port = 8000,
    [string]$TaskName = "WhisperTranscriptor",
    [string]$WorkingDir = (Get-Location).Path,
    [switch]$AddFirewallRule
)

if (-not ([bool](Get-Process -Id $PID -ErrorAction SilentlyContinue))) {
    # noop
}

# Resolve repo-relative paths
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$runScript = Join-Path $scriptDir "run_server.ps1"
if (-not (Test-Path $runScript)) { Write-Error "run_server.ps1 not found in scripts/ — ensure you're running from repo root."; exit 1 }

if (-not $PythonExe) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) { $PythonExe = $pythonCmd.Source }
}

if (-not (Test-Path $PythonExe)) { Write-Error "python executable not found; pass -PythonExe or ensure python is on PATH."; exit 1 }

# Build the command that the scheduled task runs.
$psCmd = "powershell -ExecutionPolicy Bypass -File `"$runScript`" -PythonExe `"$PythonExe`" -BindHost $Host -Port $Port -WorkingDir `"$WorkingDir`""

Write-Output "Creating scheduled task '$TaskName' (runs at system startup as SYSTEM)..."
# Use schtasks so we can register as SYSTEM without credential prompt
schtasks /Create /SC ONSTART /TN "$TaskName" /TR "$psCmd" /RL HIGHEST /F /RU "SYSTEM" | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create scheduled task (schtasks exit $LASTEXITCODE). Run PowerShell as Administrator."; exit 1
}

Write-Output "Task created. Starting task now..."
schtasks /Run /TN "$TaskName" | Out-Null

if ($AddFirewallRule) {
    Write-Output "Adding Windows Firewall rule for TCP port $Port..."
    netsh advfirewall firewall add rule name="$TaskName (port $Port)" dir=in action=allow protocol=TCP localport=$Port | Out-Null
}

Write-Output "Done. Access the UI via your Tailscale IP (example: http://100.67.71.101:$Port) once the service is up. Check storage\server.out.log (stdout) and storage\server.err.log (stderr) for details."