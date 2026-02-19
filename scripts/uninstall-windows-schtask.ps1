<#
Remove the scheduled task and optional firewall rule.
Usage (Admin PowerShell):
  .\uninstall-windows-schtask.ps1 -TaskName "WhisperTranscriptor" -Port 8000 -RemoveFirewallRule
#>
param(
    [string]$TaskName = "WhisperTranscriptor",
    [int]$Port = 8000,
    [switch]$RemoveFirewallRule
)

Write-Output "Stopping and deleting scheduled task '$TaskName'..."
try {
    schtasks /End /TN "$TaskName" 2>$null | Out-Null
} catch {}

schtasks /Delete /TN "$TaskName" /F | Out-Null

if ($RemoveFirewallRule) {
    Write-Output "Removing firewall rule for port $Port..."
    netsh advfirewall firewall delete rule name="$TaskName (port $Port)" protocol=TCP localport=$Port | Out-Null
}

Write-Output "Cleanup complete."