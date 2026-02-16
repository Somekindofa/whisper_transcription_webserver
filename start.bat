@echo off
REM Whisper Transcription Server - Quick Start Launcher
REM Double-click this file to start the server

echo.
echo ============================================================
echo   Whisper Transcription Server - Quick Start
echo ============================================================
echo.

REM Set environment variable to fix OpenMP duplicate library error
set KMP_DUPLICATE_LIB_OK=TRUE

REM Start the server using the launcher
echo Starting server...
echo.
conda run -n whisper_transcriptor python launcher.py

REM If conda command fails, show helpful message
if errorlevel 1 (
    echo.
    echo ERROR: Failed to start server
    echo.
    echo Please make sure:
    echo   1. Conda is installed
    echo   2. You've run: conda env create -f environment.yml
    echo   3. The whisper_transcriptor environment exists
    echo.
    pause
)
