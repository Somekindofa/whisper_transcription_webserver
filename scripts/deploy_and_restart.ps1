<#
Pull latest from origin/<Branch> and restart the server.
Intended for use by deploy scripts, CI, or manual remote SSH.

Usage:
  .\scripts\deploy_and_restart.ps1               # pulls origin/master (default)
  .\scripts\deploy_and_restart.ps1 -Branch main
  ssh user@host "powershell -File C:\...\deploy_and_restart.ps1 -Branch master"
#>
param(
    [string]$Branch = 'master',
    [string]$WorkingDir = ""
)

Set-StrictMode -Version Latest

if (-not $WorkingDir) { $WorkingDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path } else { $WorkingDir = (Resolve-Path -Path $WorkingDir).Path }

Write-Output "Deploy: branch=$Branch, workingDir=$WorkingDir"

Push-Location $WorkingDir
try {
    $gitCmd = Get-Command git -ErrorAction SilentlyContinue
    if (-not $gitCmd) { throw "git not found on PATH" }

    # Ensure remote branch exists, fall back to main if needed
    $remoteBranchExists = (& git ls-remote --heads origin $Branch) -ne $null
    if (-not $remoteBranchExists) {
        Write-Output "origin/$Branch not found — attempting origin/main"
        $Branch = 'main'
    }

    Write-Output "Fetching origin/$Branch..."
    & git fetch origin $Branch --prune
    Write-Output "Resetting working tree to origin/$Branch"
    & git reset --hard origin/$Branch
    & git clean -fd

    # Optional: install python deps if requirements.txt changed
    if (Test-Path "requirements.txt") {
        $py = (Get-Command python -ErrorAction SilentlyContinue)
        if ($py) {
            Write-Output "Installing/refreshing Python dependencies (requirements.txt)..."
            & $py.Source -m pip install -r requirements.txt
        } else {
            Write-Output "Python not on PATH — skipping pip install step."
        }
    }

    # Run migrations / other post-deploy steps here if required

    # Restart the app
    Write-Output "Invoking restart..."
    $restart = Join-Path $PSScriptRoot 'restart-server.ps1'
    & powershell -NoProfile -ExecutionPolicy Bypass -File $restart -WorkingDir $WorkingDir

    Write-Output "Deploy complete."
} finally {
    Pop-Location
}
