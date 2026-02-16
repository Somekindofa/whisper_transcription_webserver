#!/usr/bin/env python3
"""
Simple Whisper Transcription Server Launcher
Just run: python launcher.py
"""

import subprocess
import sys
import os

def main():
    # Fix OpenMP duplicate initialization error
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    print("\n" + "="*60)
    print("  Whisper Transcription Server")
    print("="*60 + "\n")
    
    print("Starting server...\n")
    print("📍 Open your browser: http://localhost:5000")
    print("⏹  Press Ctrl+C to stop\n")
    
    # Start the app
    try:
        subprocess.run(
            "conda run -n whisper_transcriptor python app.py",
            shell=True,
            check=False
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
