# Project Summary: Whisper Transcription Webserver

## Overview

A professional-grade, GPU-accelerated local webserver for transcribing audio and video files using OpenAI's Whisper v3 large model. Designed for high-performance processing on workstations with powerful GPUs.

## What's Included

### Backend Components
- **app.py** - Flask-based server with Whisper integration
  - CUDA GPU acceleration for fast transcription
  - Parallel file processing using ThreadPoolExecutor
  - Support for audio extraction from video files using FFmpeg
  - RESTful API endpoints for upload, status, and download
  - Real-time job status tracking

### Frontend Components
- **templates/index.html** - Single-page web application
  - Modern light theme with purple-blue gradients
  - Drag-and-drop file upload interface
  - File picker for browser selection
  - Real-time progress bars for each file
  - Language detection display
  - Individual and batch download capabilities
  - Responsive design for desktop and mobile

### Configuration & Utilities
- **environment.yml** - Conda dependencies (Flask, Torch, Whisper, etc.)
- **config.py** - Configuration options for customization
- **run.bat** - Windows batch script for easy startup (auto-setup)
- **run.ps1** - PowerShell script alternative for Windows
- **setup.py** - Conda setup script for dependency installation

### Documentation
- **README.md** - Comprehensive documentation
  - Features and requirements
  - Installation instructions (Windows, Linux, macOS)
  - Usage guide
  - Troubleshooting
  - Performance tips
  - API documentation

- **QUICKSTART.md** - Quick start guide
  - First-time setup (Windows focused)
  - Basic workflow
  - Troubleshooting common issues
  - Tips and tricks

- **DEPLOYMENT.md** - Advanced deployment guide
  - System setup (Windows, Linux, macOS)
  - Production deployment (Gunicorn, Nginx)
  - Performance tuning
  - Docker deployment
  - Monitoring and logging

## Key Features Implemented

### ✅ File Upload & Processing
- [x] Drag-and-drop file upload
- [x] File picker dialog
- [x] Multiple file batch processing
- [x] Support for: MP3, WAV, FLAC, OGG, M4A (audio)
- [x] Support for: MP4, MOV, AVI, MKV (video with auto audio extraction)
- [x] Parallel processing (4 concurrent files by default)
- [x] File size limit: 500MB per file

### ✅ GPU Acceleration
- [x] CUDA support for NVIDIA GPUs
- [x] Automatic GPU detection
- [x] Falls back to CPU if GPU unavailable
- [x] FP16 optimization for faster inference
- [x] GPU memory management

### ✅ Real-time User Interface
- [x] Live progress bars for each file
- [x] Status updates (Queued → Extracting Audio → Transcribing → Completed)
- [x] Language detection display
- [x] Transcription preview
- [x] Error messages with details
- [x] Responsive design

### ✅ File Management
- [x] Individual file download as text
- [x] Batch download as ZIP
- [x] Clear completed/failed jobs
- [x] Automatic cleanup of temporary files
- [x] Output folder for result storage

### ✅ UI/UX Design
- [x] Light theme
- [x] Purple-blue gradient styling
- [x] Modern card-based layout
- [x] Smooth animations and transitions
- [x] Intuitive status indicators
- [x] Accessible color scheme

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Web Browser                          │
│         (index.html with CSS & JavaScript)             │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/WebSocket
┌────────────────────▼────────────────────────────────────┐
│              Flask Web Server (app.py)                   │
│                                                          │
│  Routes:                                                │
│  - GET  /              → Serve index.html              │
│  - POST /api/upload    → Handle file uploads           │
│  - GET  /api/status    → Get job status                │
│  - GET  /api/download  → Download transcription        │
│  - POST /api/batch-download → Download ZIP             │
│  - POST /api/clear-jobs → Clear completed jobs         │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
    ┌────────────────────────────────────┐
    │      ThreadPoolExecutor (4x)       │
    │   - Parallel job processing        │
    │   - Real-time status updates       │
    └────────────────────┬───────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │  FFmpeg  │   │ Whisper  │   │ PyTorch  │
    │(Video)   │   │(Model)   │   │  (CUDA)  │
    └──────────┘   └──────────┘   └──────────┘
                         │
                         ▼
                    ┌────────────┐
                    │ NVIDIA GPU │
                    │  (CUDA)    │
                    └────────────┘
```

## Technology Stack

### Backend
- **Flask** - Web framework
- **PyTorch** - Deep learning framework with CUDA support
- **OpenAI Whisper** - Speech-to-text model
- **FFmpeg** - Audio/video processing (external)
- **Python** - Programming language (via Conda)

### Frontend
- **HTML5** - Markup
- **CSS3** - Styling with gradients and animations
- **Vanilla JavaScript** - No dependencies (lightweight)
- **Fetch API** - Server communication

### Optional (Production)
- **Gunicorn** - WSGI server
- **Nginx** - Reverse proxy
- **Docker** - Containerization

## Getting Started

### Quick Start (Windows - Easiest)
```
1. Double-click run.bat
2. Wait for setup to complete
3. Browser opens to http://localhost:5000
4. Start transcribing!
```

### Manual Start
```
conda env update -f environment.yml --prune
conda run -n whisper_transcriptor python app.py
```

### First Run Notes
- First time model loading takes 2-3 minutes (downloads ~3GB model)
- GPU VRAM should be 6GB+ for large-v3 model
- Can use smaller models if needed (base, small, medium)

## Performance Metrics

### Expected Processing Speed
**RTX 3080 (10GB VRAM):**
- 1 minute audio: 2-5 seconds
- 1 hour audio: 3-5 minutes
- 4 files in parallel: Linear scaling

**RTX 2080/GTX 1080:**
- 1 minute audio: 10-20 seconds
- 1 hour audio: 15-30 minutes

**CPU Only (Not Recommended):**
- 10-30x slower than GPU
- 1 minute audio: 1-2 minutes

## API Endpoints

### POST /api/upload
Upload files for transcription
```
Request: multipart/form-data with files[]
Response: { job_ids: [...], message: "..." }
```

### GET /api/status/<job_id>
Get job status and progress
```
Response: {
  job_id: "...",
  status: "queued|extracting_audio|transcribing|completed|failed",
  filename: "...",
  progress: 0-100,
  transcription: "...",
  language: "en",
  error: null
}
```

### GET /api/download/<job_id>
Download individual transcription

### POST /api/batch-download
Download multiple transcriptions as ZIP

### POST /api/clear-jobs
Clear completed/failed jobs

## Configuration Options

Key settings in `app.py` and `config.py`:
- Server host/port
- Whisper model (tiny, base, small, medium, large, large-v3)
- Number of parallel workers (1-8 recommended)
- Max file size (default 500MB)
- CUDA/CPU device selection
- Upload/output folders

## Security Considerations

✅ **Secure by Default:**
- All processing is local (no external API calls)
- Files stored temporarily in local folders
- No data transmission over internet

⚠️ **For Production:**
- Add API key authentication
- Implement CORS properly
- Use HTTPS with SSL certificates
- Add rate limiting
- Validate file uploads
- Run behind Nginx/Gunicorn

## Troubleshooting

### Common Issues & Solutions

1. **CUDA not available**
   - Check: `nvidia-smi`
   - Update GPU drivers
   - Reinstall PyTorch with CUDA support

2. **FFmpeg not found**
   - Install from https://ffmpeg.org/
   - Add to Windows PATH

3. **Port 5000 in use**
   - Change port in app.py
   - Or kill process using port

4. **Out of VRAM**
   - Reduce parallel workers
   - Use smaller model
   - Close other GPU apps

5. **Files stuck processing**
   - Check GPU memory
   - Monitor with `nvidia-smi`
   - Restart server if needed

## Future Enhancement Ideas

- [ ] Speaker diarization
- [ ] Multiple language support UI
- [ ] Transcription editing interface
- [ ] Integration with cloud storage (Google Drive, OneDrive)
- [ ] Webhook support for external processing
- [ ] Web-based queue management
- [ ] Advanced filtering and search
- [ ] Export to multiple formats (JSON, SRT, VTT)
- [ ] Real-time transcription from microphone
- [ ] User authentication and per-user folders

## File Structure

```
whisper_transcriptor/
├── app.py                    # Main Flask application
├── config.py                 # Configuration file
├── setup.py                  # Setup script
├── run.bat                   # Windows startup (batch)
├── run.ps1                   # Windows startup (PowerShell)
├── environment.yml           # Conda environment
├── .gitignore               # Git ignore rules
├── README.md                # Main documentation
├── QUICKSTART.md            # Quick start guide
├── DEPLOYMENT.md            # Advanced deployment guide
├── templates/
│   └── index.html           # Web UI
├── uploads/                 # Temporary file storage
├── outputs/                 # Transcription results
```

## System Requirements

### Minimum
- Conda (Miniconda/Anaconda)
- 8GB RAM
- 20GB disk space (for model + files)
- NVIDIA GPU with 6GB+ VRAM (or CPU fallback)

### Recommended
- Conda (latest)
- 16GB+ RAM
- 50GB disk space
- NVIDIA RTX 3080 or newer (10GB+ VRAM)
- SSD for faster processing

## Performance Tips

1. **GPU:** Keep at least 6GB VRAM available
2. **Batch:** Upload multiple files for parallel processing
3. **Model:** Use smaller models for faster processing
4. **Disk:** Use SSD for better I/O performance
5. **Network:** Close browser if lag when scrolling

## Dependencies

### Core
- flask==3.0.0
- torch==2.1.2 (with CUDA)
- torchaudio==2.1.2
- openai-whisper==20231117

### External Tools
- FFmpeg (for video support)
- NVIDIA CUDA Toolkit (for GPU)

## License & Credits

- Built with OpenAI's Whisper model
- Flask web framework
- PyTorch deep learning framework
- Modern web technologies (HTML5, CSS3, ES6+)

## Support & Documentation

1. **QUICKSTART.md** - Get running in 5 minutes
2. **README.md** - Comprehensive guide
3. **DEPLOYMENT.md** - Advanced setup and production deployment
4. **config.py** - Inline configuration documentation
5. **app.py** - Well-commented source code

---

**Ready to transcribe!** 🎙️

Start with QUICKSTART.md for fastest setup, or README.md for detailed information.
