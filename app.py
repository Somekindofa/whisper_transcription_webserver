#!/usr/bin/env python
"""
Whisper Transcriptor - Audio/Video transcription with speaker diarization
Entry point for running the FastAPI server
"""

if __name__ == "__main__":
    import uvicorn
    from server import config
    
    print("=" * 60)
    print("Whisper Transcriptor")
    print("=" * 60)
    print(f"Starting server at http://{config.HOST}:{config.PORT}")
    print(f"Whisper model: {config.WHISPER_MODEL}")
    print(f"Device: {config.WHISPER_DEVICE}")
    print(f"Compute type: {config.WHISPER_COMPUTE_TYPE}")
    print("=" * 60)
    
    uvicorn.run(
        "server.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
        log_level="info",
    )
