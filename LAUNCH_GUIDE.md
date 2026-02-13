# 🎙️ Whisper Transcription Server - Setup & Launch Guide

## ⚡ FASTEST START (60 Seconds)

### Windows Users
```
1. Double-click: run.bat
2. Wait for: "Server is starting..."
3. Open browser: http://localhost:5000
✅ Done! Start uploading files
```

### Linux/Mac Users
```
conda env update -f environment.yml --prune
conda run -n whisper_transcriptor python app.py
# Then open: http://localhost:5000
```

---

## 📋 Pre-Flight Checklist

Before you start, verify you have:

```
Hardware:
□ NVIDIA GPU (or will use CPU)
□ 8GB+ RAM
□ 20GB+ disk space
□ Modern web browser

Software:
□ Conda (Miniconda/Anaconda) installed
□ FFmpeg installed (for video files)
□ CUDA drivers updated (if using GPU)
```

**Check:**
```bash
conda --version           # Should show conda version
nvidia-smi               # Should show your GPU (if you have one)
ffmpeg -version          # Should show version
```

---

## 🚀 Installation Steps

### Step 1: Verify Prerequisites (5 minutes)
```bash
# Check Conda
conda --version
# Output: conda version ✓

# Check GPU (optional)
nvidia-smi
# Output: Your GPU name ✓

# Check FFmpeg
ffmpeg -version
# Output: Version info ✓
```

### Step 2: Download/Clone Project (Already Done!)
✅ You have all files in: `whisper_transcriptor/`

### Step 3: Install Dependencies (5-10 minutes)

**Option A: Automatic (Windows - Recommended)**
```
Double-click: run.bat
Everything is handled automatically!
```

**Option B: Automatic (PowerShell)**
```powershell
powershell -ExecutionPolicy Bypass -File run.ps1
```

**Option C: Manual**
```bash
conda env update -f environment.yml --prune
```

### Step 4: Download Whisper Model (2-3 minutes on first run)
This happens automatically when you:
```bash
conda run -n whisper_transcriptor python app.py
```

---

## ✅ Verification Checklist

After installation, verify everything works:

```
□ Server runs without errors
□ Terminal shows: "Running on http://127.0.0.1:5000"
□ Browser opens to http://localhost:5000
□ Upload area is visible with purple gradient
□ File picker button works
□ GPU is detected (check nvidia-smi)
□ You can upload a test file
□ Progress bar appears
□ Transcription completes
□ Download button appears
□ Downloaded file is readable
```

---

## 🎯 First Time User Flow

```
┌─────────────────────────────────────────────────┐
│ 1. Run Server                                   │
│    Windows: double-click run.bat                │
│    Other: conda run -n whisper_transcriptor python app.py │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│ 2. Open Browser                                 │
│    Go to: http://localhost:5000                 │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│ 3. Upload Files                                 │
│    Drag files or click "Browse Files"           │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│ 4. Watch Progress                               │
│    See real-time progress bars                  │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│ 5. Download Results                             │
│    Click "Download" or "Download All"           │
│    Select save location                         │
└─────────────────────────────────────────────────┘
```

---

## 📊 What to Expect

### Installation Time
- **Fast (SSD, good connection):** 5-10 minutes
- **Normal:** 10-15 minutes
- **Slow (HDD, slow connection):** 20-30 minutes

### First Run
- **First time only:** Downloads ~3GB Whisper model (2-3 minutes)
- **Subsequent runs:** Model already cached

### Processing Speed
- **With GPU (RTX 3080+):** 1 min audio → 2-5 sec
- **With older GPU:** 1 min audio → 10-30 sec
- **CPU only:** 1 min audio → 1-2 min (not recommended)

---

## 🎨 UI Overview

```
┌────────────────────────────────────────────────────┐
│                                                    │
│        🎙️ Whisper Transcription                   │
│   Fast GPU-powered transcription with drag & drop  │
│                                                    │
├────────────────────┬─────────────────────────────┤
│   Upload Files     │  Transcriptions             │
│                    │                             │
│  ┌──────────────┐  │  No files uploaded yet      │
│  │ Drag & drop  │  │                             │
│  │ or browse    │  │  (Files appear here)        │
│  └──────────────┘  │                             │
│                    │                             │
│  📂 Browse Files   │  ⬇️ Download All (appears) │
│                    │  🗑️ Clear (appears)        │
└────────────────────┴─────────────────────────────┘
```

---

## 🔧 Troubleshooting Quick Fixes

### Server Won't Start
```bash
# Problem: Module not found errors
# Solution:
conda env update -f environment.yml --prune

# Problem: Port already in use
# Solution:
# Edit app.py, change: app.run(port=5001)

# Problem: Conda not found
# Solution:
# Add Conda to PATH during installation
```

### GPU Not Being Used
```bash
# Check GPU
nvidia-smi

# Update drivers from:
# https://www.nvidia.com/Download/index.aspx

# Reinstall PyTorch with CUDA:
conda install -n whisper_transcriptor -c pytorch -c nvidia pytorch torchaudio
```

### FFmpeg Not Found
```bash
# Windows: Download from https://ffmpeg.org/download.html
# Mac: brew install ffmpeg
# Linux: sudo apt-get install ffmpeg

# Add to PATH
# Then restart the server
```

### Out of VRAM
```
# Solutions:
1. Close other GPU applications
2. Use smaller model: "medium" or "base"
3. Reduce parallel workers to 1-2
4. Process files one at a time
```

---

## 📚 Documentation Files

After you get it running, read these in order:

| File | Time | Purpose |
|------|------|---------|
| `START_HERE.md` | 2 min | Project overview |
| `QUICKSTART.md` | 5 min | Setup & basic use |
| `README.md` | 15 min | Complete reference |
| `DEPLOYMENT.md` | 20 min | Production setup |
| `config.py` | 5 min | Customization options |

---

## 🎯 Common Tasks

### Upload Files
- Drag files onto purple box
- Or click "📂 Browse Files"
- Supports: MP3, WAV, FLAC, MP4, MOV, AVI, MKV, etc.

### Watch Progress
- Progress bars show in real-time
- Status updates every 0.5 seconds
- 4 files process in parallel by default

### Download Results
- Individual file: Click "⬇️ Download"
- All files: Click "⬇️ Download All"
- Files save to your Downloads folder

### Speed Up Processing
- Upload multiple files at once
- Use GPU (check with nvidia-smi)
- Try smaller model ("medium" vs "large-v3")
- Ensure no other GPU apps running

---

## 🌐 Network Access

### Local Only (Default - Secure)
- Only accessible from your computer
- No firewall issues
- Private and safe

### Network Access (Advanced)
To allow access from other computers:
1. Edit `app.py`
2. Change: `app.run(host='127.0.0.1')`
3. To: `app.run(host='0.0.0.0')`
4. Access from other machines using your IP:
   - `http://192.168.1.100:5000`

---

## 🔒 Security Notes

✅ **Secure by Default:**
- All processing is local
- No files sent to cloud
- No external API calls
- Data stays on your computer

⚠️ **If exposing to network:**
- Add authentication
- Use HTTPS
- Implement rate limiting
- See DEPLOYMENT.md

---

## 💡 Pro Tips

1. **Batch Processing:** Upload 4-8 files at once for best GPU utilization
2. **Monitor GPU:** Use `nvidia-smi -l 1` to watch GPU usage
3. **Large Files:** Split very long videos/audios into chunks
4. **Model Selection:** Use "small" for 3GB VRAM, "medium" for 6GB, "large-v3" for 10GB+
5. **Disk Space:** Keep 50GB+ free for model cache + uploads
6. **SSD:** Use SSD for faster I/O performance

---

## 📞 Getting Help

1. **Basic questions:** Check `QUICKSTART.md`
2. **Detailed help:** Check `README.md`
3. **Advanced setup:** Check `DEPLOYMENT.md`
4. **Code questions:** Check `app.py` comments
5. **Configuration:** Check `config.py`

---

## 🎬 Example Workflow

```
1. Server running at http://localhost:5000
   └─ Terminal shows: "Running on http://127.0.0.1:5000"

2. Open browser to http://localhost:5000
   └─ See purple gradient upload interface

3. Upload 3 audio files at once
   └─ Files appear in list with "Queued" status

4. Files start processing
   └─ Progress bars appear and update in real-time
   └─ Status: Extracting Audio → Transcribing

5. First file completes after ~20 seconds
   └─ Shows green "✓ Completed" badge
   └─ Shows detected language
   └─ Preview text appears

6. All files complete
   └─ "⬇️ Download All" button appears
   └─ Click to download ZIP file
   └─ Select save location

7. All transcriptions saved to Downloads folder!
   └─ One .txt file per original file
```

---

## ✨ Features You Have

- ✅ GPU acceleration (CUDA)
- ✅ Drag & drop upload
- ✅ Multiple file formats
- ✅ Parallel processing (4 concurrent)
- ✅ Real-time progress
- ✅ Batch downloads
- ✅ Language detection
- ✅ Beautiful modern UI
- ✅ Local processing (private)
- ✅ Easy configuration

---

## 🚀 Ready to Start?

### Option 1: Windows (Easiest)
```
1. Open whisper_transcriptor folder
2. Double-click: run.bat
3. Wait for "Server is starting..."
4. Start uploading! 🎉
```

### Option 2: Command Line
```bash
python app.py
```

### Option 3: Read More First
1. Read: `START_HERE.md` (2 min)
2. Read: `QUICKSTART.md` (5 min)
3. Then start server!

---

## 📈 Performance Expectations

```
GPU: RTX 3080 (10GB VRAM)
├─ 1 minute audio: 2-5 seconds
├─ 10 minutes audio: 20-50 seconds
└─ 1 hour audio: 3-5 minutes

GPU: RTX 2080 (8GB VRAM)
├─ 1 minute audio: 10-20 seconds
├─ 10 minutes audio: 2-3 minutes
└─ 1 hour audio: 15-30 minutes

CPU: Intel i9 (No GPU)
├─ 1 minute audio: 1-2 minutes (not recommended)
```

---

**Everything is ready. Start with `run.bat` now!** 🎙️✨

Questions? Check `QUICKSTART.md` or `README.md`
