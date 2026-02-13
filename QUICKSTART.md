# Quick Start Guide

## First Time Setup (Windows)

1. **Install FFmpeg** (needed for video support)
   - Download: https://ffmpeg.org/download.html
   - Extract to `C:\ffmpeg`
   - Add to PATH or just keep it simple

2. **Run the server**
   - Double-click `run.bat`
   - The script will:
   - Create/update the conda environment
   - Install all dependencies (takes 5-10 minutes)
     - Download the Whisper model (takes 2-3 minutes on first run)
     - Start the server

3. **Open in browser**
   - After seeing "Server is starting..."
   - Go to http://localhost:5000
   - You're ready!

## Using the Interface

### Basic Workflow

1. **Upload Files**
   - Drag & drop audio/video files onto the upload area
   - Or click "Browse Files" button
   - Multiple files at once is supported!

2. **Wait for Processing**
   - Watch the progress bars update in real-time
   - Each file shows its status (Extracting Audio, Transcribing, etc.)
   - GPU acceleration makes this fast!

3. **Download Results**
   - Click "Download" on individual files
   - Click "Download All" to get everything as a ZIP
   - Files save to your Downloads folder

### Supported File Types

**Audio (Direct)**
- MP3, WAV, FLAC, OGG, M4A

**Video (Audio Auto-Extracted)**
- MP4, MOV, AVI, MKV

## Performance Expectations

### With Good GPU (RTX 3080+)
- 1 minute audio → 2-5 seconds
- 1 hour audio → 3-5 minutes
- Process 4 files in parallel

### With Older GPU (RTX 2080, GTX 1080)
- 1 minute audio → 10-20 seconds
- 1 hour audio → 15-30 minutes

### With CPU Only
- Much slower (10-30x)
- 1 minute → 1-2 minutes
- Not recommended

## Troubleshooting

### "FFmpeg not found" error
- Install FFmpeg from https://ffmpeg.org/download.html
- Add to Windows PATH
- Or set environment variable

### GPU not being used
- Check: Run `nvidia-smi` in command prompt
- Verify GPU drivers are up-to-date
- Check VRAM usage while transcribing

### Server won't start
- Make sure port 5000 is not in use
- Check Conda installation
- Run `run.bat` from command prompt to see error details

### Files stuck on "Processing"
- Check GPU memory: `nvidia-smi`
- Reduce number of parallel files
- Try smaller Whisper model

## Tips & Tricks

1. **Batch Processing**
   - Drag multiple files at once for parallel processing
   - Much faster than one at a time!

2. **Large Files**
   - Files up to 500MB supported
   - Split very long recordings for better performance

3. **Different Languages**
   - Whisper automatically detects language
   - Check the detected language badge on completed files

4. **Network Access**
   - Only accessible on `localhost:5000` by default
   - Safe to share on local network if needed
   - Add authentication for production use

## File Management

- **Uploads**: Stored in `uploads/` folder (cleaned after processing)
- **Outputs**: Transcription files saved in `outputs/` folder
- **Downloads**: Use the "Download" button for save-as dialog

## Keyboard Shortcuts

- **Browse**: Click any file item to expand/collapse
- **Clear**: Right-click to remove individual files
- **Batch**: "Clear" button removes completed files from display

## Advanced

### Change Port
Edit `app.py`, change:
```python
app.run(port=5001)  # Instead of 5000
```

### Use Smaller/Faster Model
Edit `app.py`, change:
```python
model = whisper.load_model("medium", device=DEVICE)
# Options: "tiny", "base", "small", "medium", "large", "large-v3"
```

### Process More Files in Parallel
Edit `app.py`, change:
```python
executor = ThreadPoolExecutor(max_workers=8)  # Instead of 4
```
(Make sure you have enough GPU VRAM!)

## Getting Help

1. Check the main README.md for detailed docs
2. Check console output for error messages
3. Verify GPU with `nvidia-smi`
4. Check disk space (needs ~6GB for model + space for uploads)

## System Requirements Check

**Before first run, verify:**

```bash
# Check Conda
conda --version
# Should show conda version

# Check GPU (if you have one)
nvidia-smi
# Should show your GPU

# Check FFmpeg
ffmpeg -version
# Should show version info
```

---

That's it! You're ready to transcribe! 🎙️

For detailed documentation, see README.md
