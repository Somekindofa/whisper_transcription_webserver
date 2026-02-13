# Whisper Transcription Webserver - Complete Project

Welcome! You have a complete, production-ready local webserver for GPU-accelerated audio and video transcription.

## 🚀 Quick Start (Choose One)

### Option 1: Windows Batch (Easiest - Recommended)
```
Double-click: run.bat
```
This will automatically set up everything and start the server.

### Option 2: PowerShell (Windows)
```powershell
powershell -ExecutionPolicy Bypass -File run.ps1
```

### Option 3: Manual (Any OS)
```bash
conda env update -f environment.yml --prune
conda run -n whisper_transcriptor python app.py
```

Then open: **http://localhost:5000**

---

## 📚 Documentation Guide

Read in this order based on your needs:

### 1. **I want to get started immediately**
   → Read: [QUICKSTART.md](QUICKSTART.md) (5 minutes)

### 2. **I need detailed instructions**
   → Read: [README.md](README.md) (Comprehensive)

### 3. **I want to deploy to production**
   → Read: [DEPLOYMENT.md](DEPLOYMENT.md) (Advanced)

### 4. **I want to understand the project**
   → Read: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

---

## 📋 What's Included

### Core Application
- **app.py** - Flask backend with Whisper integration
  - CUDA GPU acceleration
  - Parallel file processing
  - REST API
  - Real-time status tracking

- **templates/index.html** - Modern web interface
  - Drag-and-drop upload
  - Progress bars
  - Batch downloads
  - Light theme with purple-blue gradients

### Setup & Configuration
- **environment.yml** - Conda environment definition
- **config.py** - Customizable settings
- **run.bat** - Windows startup (auto-setup)
- **run.ps1** - PowerShell alternative
- **setup.py** - Conda setup script

### Documentation
- **QUICKSTART.md** - Fast setup guide
- **README.md** - Full documentation
- **DEPLOYMENT.md** - Production deployment
- **PROJECT_SUMMARY.md** - Project overview

---

## ⚡ Features

✅ **GPU Acceleration** - Fast transcription using CUDA
✅ **Parallel Processing** - Handle multiple files simultaneously
✅ **Drag & Drop** - Simple file upload interface
✅ **Video Support** - Auto-extracts audio from MP4/AVI/MOV/MKV
✅ **Progress Tracking** - Real-time status bars
✅ **Batch Download** - Download all transcriptions as ZIP
✅ **Modern UI** - Beautiful light theme with gradients
✅ **Local Processing** - Everything stays on your machine

---

## 🎯 System Requirements

- **Conda:** Miniconda or Anaconda
- **GPU:** NVIDIA (6GB+ VRAM recommended)
- **RAM:** 8GB+
- **Disk:** 20GB+ (for model + files)
- **FFmpeg:** For video support

---

## 🔧 First-Time Setup Checklist

### Windows Users (Easiest)
1. ✅ Double-click `run.bat`
2. ✅ Wait 5-10 minutes for setup
3. ✅ Browser opens automatically
4. ✅ Start uploading files!

### Linux/Mac Users
1. ✅ Ensure Conda is installed
2. ✅ Install FFmpeg: `brew install ffmpeg` (Mac) or `apt-get install ffmpeg` (Linux)
3. ✅ Run: `python setup.py`
4. ✅ Run: `conda run -n whisper_transcriptor python app.py`
5. ✅ Open: http://localhost:5000

---

## 🎬 Basic Usage

1. **Upload Files**
   - Click "Browse Files" or drag files onto the upload area
   - Support: MP3, WAV, FLAC, OGG, M4A, MP4, MOV, AVI, MKV
   - Multiple files at once OK!

2. **Wait for Processing**
   - Watch progress bars update in real-time
   - GPU processes files in parallel
   - Typical: 1 hour audio takes 3-5 minutes

3. **Download Results**
   - Click "Download" for individual files
   - Click "Download All" for ZIP archive
   - Files saved to your Downloads folder

---

## ⚙️ Configuration

Key settings in **config.py** or **app.py**:

```python
# Change model for faster/slower processing
WHISPER_MODEL = "large-v3"  # Options: tiny, base, small, medium, large

# Change number of parallel files
MAX_PARALLEL_WORKERS = 4

# Change port
SERVER_PORT = 5000
```

---

## 🐛 Troubleshooting

### "GPU not found"
```bash
# Check GPU
nvidia-smi

# Update CUDA drivers
# Visit: https://developer.nvidia.com/cuda-downloads
```

### "FFmpeg not found"
```bash
# Install FFmpeg
# Windows: https://ffmpeg.org/download.html
# Mac: brew install ffmpeg
# Linux: sudo apt-get install ffmpeg
```

### "Port 5000 already in use"
- Change port in app.py: `app.run(port=5001)`
- Or kill process using port 5000

### Still stuck?
- See [QUICKSTART.md](QUICKSTART.md) troubleshooting section
- See [README.md](README.md) troubleshooting section
- Check console output for error details

---

## 📊 Performance Tips

1. **GPU:** Monitor with `nvidia-smi -l 1`
2. **Batch:** Upload multiple files for faster processing
3. **Models:** Use smaller models if VRAM limited
4. **Disk:** Use SSD for better I/O performance

---

## 🔐 Security Notes

✅ **Secure:**
- All processing is local
- No external API calls
- Data stays on your machine

⚠️ **For Production:**
- Add authentication
- Use HTTPS
- Implement CORS properly
- See DEPLOYMENT.md for details

---

## 📞 Quick Reference

| Task | How To |
|------|--------|
| Start Server | `run.bat` (Windows) or `python app.py` |
| Access UI | http://localhost:5000 |
| Monitor GPU | `nvidia-smi -l 1` |
| Change Port | Edit `app.py`, change port in `app.run()` |
| Use Smaller Model | Edit `app.py`, change `WHISPER_MODEL` |
| More Parallel Files | Edit `app.py`, increase `max_workers` |
| See API Endpoints | Read [README.md](README.md#api-endpoints) |
| Deploy to Production | Read [DEPLOYMENT.md](DEPLOYMENT.md) |

---

## 🎨 UI Features

- **Drag & Drop:** Upload files by dragging
- **Progress Bars:** Real-time transcription progress
- **Status Badges:** Queued → Extracting → Transcribing → Complete
- **Language Detection:** Shows detected language
- **Batch Actions:** Download all or clear completed
- **Transcription Preview:** See first 200 characters
- **Error Messages:** Helpful error details if something fails

---

## 🚀 Next Steps

1. **Immediate:** Start `run.bat` and begin transcribing
2. **Soon:** Read [QUICKSTART.md](QUICKSTART.md) for tips
3. **Later:** Read [README.md](README.md) for full documentation
4. **Advanced:** Read [DEPLOYMENT.md](DEPLOYMENT.md) for production setup

---

## 💡 Pro Tips

- Upload 4+ files at once for best GPU utilization
- For MP4 files, audio is automatically extracted
- Download as ZIP to get all transcriptions at once
- Check GPU memory with `nvidia-smi` if processing slows down
- Try smaller model ("medium") if running out of VRAM

---

## 🎯 Everything You Need

✅ Backend server with GPU acceleration
✅ Beautiful modern web interface
✅ Drag-and-drop file upload
✅ Real-time progress tracking
✅ Batch processing support
✅ Download functionality
✅ Complete documentation
✅ Easy setup scripts
✅ Production deployment guide
✅ Troubleshooting guides

---

**Ready to transcribe? Start with `run.bat` now!** 🎙️✨

For questions, check the appropriate documentation file above.
