<#
Restart the Whisper Transcriptor application that was started with `run_server.ps1`.
- Stops any running python processes whose command line contains `app.py` from this repo
- Starts a fresh background process via `run_server.ps1` (same behavior as installer)

Usage:
  .\scripts\restart-server.ps1
  .\scripts\restart-server.ps1 -WorkingDir "C:\path\to\whisper_transcriptor"
  .\scripts\restart-server.ps1 -PythonExe "C:\Python\python.exe"
#>
param(
    [string]$WorkingDir = "",
    [string]$PythonExe = ""
)

Set-StrictMode -Version Latest

if (-not $WorkingDir) {
    $WorkingDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
} else {
    $WorkingDir = (Resolve-Path -Path $WorkingDir).Path
}

# Resolve python if not provided
if (-not $PythonExe) {
    $py = (Get-Command python -ErrorAction SilentlyContinue)
    if ($py) { $PythonExe = $py.Source }
}

Write-Output "Restart: working dir = $WorkingDir"

# Find processes running app.py in this working dir
$escaped = [regex]::Escape($WorkingDir)
$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'app.py' -and $_.CommandLine -match $escaped }

if ($procs) {
    Write-Output "Stopping $($procs.Count) running process(es) for app.py..."
    foreach ($p in $procs) {
        try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {}
    }
    Start-Sleep -Seconds 1
} else {
    Write-Output "No running app.py processes found."
}

# Start new background process using run_server.ps1
$runScript = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Definition) 'run_server.ps1'
if (-not (Test-Path $runScript)) {
    Write-Error "run_server.ps1 not found at $runScript"
    exit 1
}

$psArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$runScript)
if ($PythonExe) { $psArgs += @('-PythonExe',$PythonExe) }
$psArgs += @('-BindHost','0.0.0.0','-Port','8000','-WorkingDir',$WorkingDir)

Start-Process -FilePath powershell -ArgumentList $psArgs -WindowStyle Hidden
Write-Output "Restart requested — new background process started. Check storage/server.out.log for output."