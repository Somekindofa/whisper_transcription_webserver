#!/usr/bin/env python3
"""
Setup script for Whisper Transcription Server (Conda)
Creates/updates the conda environment and prepares the system
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description=""):
    """Run a command and handle errors."""
    if description:
        print(f"\n{description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=False)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Command failed with return code {e.returncode}")
        return False

def main():
    print("\n" + "="*60)
    print("Whisper Transcription Server - Setup")
    print("="*60 + "\n")

    # Check Conda availability
    conda_check = subprocess.run("conda --version", shell=True, capture_output=True)
    if conda_check.returncode != 0:
        print("ERROR: Conda is required but was not found in PATH")
        print("Install Miniconda from: https://docs.conda.io/en/latest/miniconda.html")
        sys.exit(1)

    print("✓ Conda detected")

    # Create necessary directories
    Path("uploads").mkdir(exist_ok=True)
    Path("outputs").mkdir(exist_ok=True)
    Path("templates").mkdir(exist_ok=True)
    print("✓ Created necessary directories")

    # Check for ffmpeg
    result = subprocess.run("ffmpeg -version", shell=True, capture_output=True)
    if result.returncode != 0:
        print("\n⚠️  WARNING: ffmpeg is not installed")
        print("   ffmpeg is required for MP4 file support")
        print("   Install from: https://ffmpeg.org/download.html")
        response = input("   Continue anyway? (y/n): ").strip().lower()
        if response != 'y':
            sys.exit(1)
    else:
        print("✓ ffmpeg is installed")

    # Create/update conda environment
    print("\nCreating/updating conda environment...")
    print("(This may take several minutes as it installs PyTorch with CUDA support)\n")

    if not run_command("conda env update -f environment.yml --prune",
                       "Updating conda environment"):
        sys.exit(1)

    print("\n✓ Conda environment ready")

    # Check CUDA
    print("\nChecking GPU support...")
    try:
        result = subprocess.run(
            "conda run -n whisper_transcriptor python -c \"import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')\"",
            shell=True
        )
        if result.returncode != 0:
            print("⚠️  Could not check CUDA - verify conda environment")
    except Exception:
        print("⚠️  Could not check CUDA - verify conda environment")

    print("\n" + "="*60)
    print("Setup Complete!")
    print("="*60)
    print("\nTo start the server, run:")
    print("  conda run -n whisper_transcriptor python app.py")
    print("\nThen open your browser and navigate to:")
    print("  http://localhost:5000")
    print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    main()
