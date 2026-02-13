# Whisper Transcription Server - PowerShell Startup Script
# Run this script to set up and start the server on Windows

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Whisper Transcription Server - GPU Powered" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Conda is installed
try {
    $condaVersion = & conda --version 2>&1
    Write-Host "✓ Conda found: $condaVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ ERROR: Conda is not installed or not in PATH" -ForegroundColor Red
    Write-Host "  Please install Miniconda from https://docs.conda.io/en/latest/miniconda.html" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Create or update conda environment
Write-Host ""
Write-Host "[1/5] Creating/updating conda environment..." -ForegroundColor Yellow
& conda env update -f environment.yml --prune
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ ERROR: Failed to create/update conda environment" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check CUDA
Write-Host "[2/5] Checking GPU support..." -ForegroundColor Yellow
$cudaCheck = & conda run -n whisper_transcriptor python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); [print(f'GPU: {torch.cuda.get_device_name(0)}') if torch.cuda.is_available() else print('GPU: None')]" 2>&1
Write-Host "      $cudaCheck" -ForegroundColor Green

# Start server
Write-Host "[3/5] Starting Whisper Transcription Server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Server is starting..." -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Open your browser and navigate to:" -ForegroundColor Green
Write-Host "  http://localhost:5000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

& conda run -n whisper_transcriptor python app.py
