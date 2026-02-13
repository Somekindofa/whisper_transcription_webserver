@echo off
REM Whisper Transcription Server Setup and Run Script for Windows

echo.
echo ================================================
echo Whisper Transcription Server - GPU Powered
echo ================================================
echo.

REM Check if Conda is installed
conda --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Conda is not installed or not in PATH
    echo Please install Miniconda or Anaconda from:
    echo https://docs.conda.io/en/latest/miniconda.html
    pause
    exit /b 1
)

echo [1/5] Conda found. Creating/updating environment...
conda env update -f environment.yml --prune
if errorlevel 1 (
    echo ERROR: Failed to create/update conda environment
    pause
    exit /b 1
)

echo [2/5] Checking CUDA availability...
conda run -n whisper_transcriptor python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"

echo [3/5] Starting Whisper Transcription Server...
echo.
echo ================================================
echo Server is starting...
echo Open your browser and navigate to:
echo http://localhost:5000
echo ================================================
echo.
echo Press Ctrl+C to stop the server
echo.

conda run -n whisper_transcriptor python app.py

pause
