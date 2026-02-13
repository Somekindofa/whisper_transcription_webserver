# Whisper Transcription Server

A fast, GPU-powered local webserver for transcribing audio and video files using OpenAI's Whisper v3 large model.

## Features

- 🚀 **GPU Acceleration**: Uses CUDA for fast processing on NVIDIA GPUs
- 🎙️ **Audio Support**: MP3, WAV, FLAC, OGG, M4A
- 🎬 **Video Support**: MP4, MOV, AVI, MKV (auto-extracts audio)
- 📁 **Drag & Drop**: Simple drag-and-drop interface
- 🔄 **Parallel Processing**: Process multiple files simultaneously
- ⏳ **Progress Tracking**: Real-time progress bars for each file
- 📊 **Batch Operations**: Download multiple transcriptions as ZIP
- 🎨 **Modern UI**: Beautiful light theme with purple-blue gradients
- 💻 **Local Processing**: All processing happens locally on your machine

## Requirements

- **Conda**: Miniconda or Anaconda
- **NVIDIA GPU**: Recommended for fast processing (Maxwell or newer)
- **CUDA**: For GPU support (optional, can run on CPU)
- **FFmpeg**: Required for video file support
- **RAM**: 8GB minimum (16GB+ recommended)
- **VRAM**: 6GB+ recommended for Whisper v3 large model

## Installation (Conda Only)

### Option 1: Windows Batch Script (Easiest)

1. Download or clone this repository
2. Double-click `run.bat`
3. Wait for conda environment setup to complete
4. Browser should open to http://localhost:5000

### Option 2: Manual Installation (Conda)

1. **Install Miniconda/Anaconda:**
   - https://docs.conda.io/en/latest/miniconda.html

2. **Create/Update the environment:**
   ```bash
   conda env update -f environment.yml --prune
   ```

3. **Run the server:**
   ```bash
   conda run -n whisper_transcriptor python app.py
   ```

4. **Open in browser:**
   Navigate to `http://localhost:5000`

### Prerequisites Setup

#### FFmpeg Installation

FFmpeg is required for MP4 and other video format support.

**Windows:**
- Download from https://ffmpeg.org/download.html
- Extract and add to PATH, or run setup.py which will guide you

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get install ffmpeg
```

#### CUDA Setup (for GPU Acceleration)

1. Ensure you have an NVIDIA GPU
2. Install NVIDIA CUDA Toolkit: https://developer.nvidia.com/cuda-downloads
3. Install cuDNN: https://developer.nvidia.com/cudnn
4. The conda environment includes PyTorch with CUDA support

**Verify CUDA installation:**
```python
import torch
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0))
```

## Usage

### Web Interface

1. **Upload Files:**
   - Click "Browse Files" button or drag files directly onto the upload area
   - Multiple files can be uploaded at once

2. **Processing:**
   - Files are automatically transcribed in parallel
   - Progress bars show the status of each file
   - Real-time updates as processing occurs

3. **Download Results:**
   - Once transcription completes, a "Download" button appears
   - Single file: Click download to save individual transcription
   - Multiple files: Click "Download All" to get a ZIP file with all transcriptions
   - Files are saved to your Downloads folder by default

### Supported Formats

**Audio Files:**
- MP3
- WAV
- FLAC
- OGG
- M4A

**Video Files (audio auto-extracted):**
- MP4
- MOV
- AVI
- MKV

### File Size Limits

- Maximum 500MB per file
- Processing time depends on file duration and GPU capability

## Performance

### Processing Speed

With an NVIDIA RTX 3080 or better:
- ~1 minute of audio → ~2-5 seconds
- Full hour of audio → ~2-5 minutes

With CPU processing:
- Much slower (10-30x slower)
- Not recommended for production use

### Batch Processing

- Up to 4 files processed in parallel by default
- Modify `ThreadPoolExecutor(max_workers=4)` in `app.py` for more/less parallelism
- GPU VRAM limits maximum concurrent processing

## Architecture

### Backend

- **Flask**: Web framework
- **Whisper**: Speech-to-text model
- **PyTorch**: Deep learning framework
- **FFmpeg**: Video processing
- **ThreadPoolExecutor**: Parallel processing

### Frontend

- **HTML5**: File API for uploads
- **CSS3**: Modern styling with gradients
- **JavaScript**: Real-time progress tracking and UI updates
- **Fetch API**: Server communication

## API Endpoints

### POST `/api/upload`
Upload audio/video files for transcription
- **Body**: FormData with `files[]` field
- **Response**: JSON with job IDs

### GET `/api/status/<job_id>`
Get transcription status and progress
- **Response**: JSON with status, filename, progress, transcription, language

### GET `/api/download/<job_id>`
Download individual transcription as text file
- **Response**: Text file download

### POST `/api/batch-download`
Download multiple transcriptions as ZIP
- **Body**: JSON with `job_ids` array
- **Response**: ZIP file download

### POST `/api/clear-jobs`
Clear completed/failed jobs from memory
- **Body**: JSON with `job_ids` array
- **Response**: Confirmation JSON

## Configuration

Edit `app.py` to customize:

- **Port**: Change `app.run(port=5000)` to desired port
- **Parallel Workers**: Change `ThreadPoolExecutor(max_workers=4)`
- **Max File Size**: Modify `MAX_FILE_SIZE` constant
- **Model**: Change from "large-v3" to smaller models like "base", "small", "medium"

## Troubleshooting

### CUDA Not Available

If GPU isn't being used:
1. Check NVIDIA drivers: `nvidia-smi`
2. Verify CUDA installation
3. Reinstall PyTorch with CUDA support:
   ```bash
   conda install -n whisper_transcriptor -c pytorch -c nvidia pytorch torchaudio
   ```

### FFmpeg Not Found

1. Install FFmpeg (see Prerequisites section)
2. Verify it's in PATH: `ffmpeg -version`

### Out of Memory

If running out of VRAM:
1. Reduce parallel workers in `app.py`
2. Use smaller Whisper model (e.g., "medium" or "base")
3. Close other GPU applications

### Port Already in Use

Change the port in `app.py`:
```python
app.run(host='0.0.0.0', port=5001, debug=False)
```

## Advanced Options

### Using Smaller Models

For faster processing on limited GPU memory, edit `app.py`:

```python
# Replace "large-v3" with:
model = whisper.load_model("medium", device=DEVICE)  # ~1.5GB VRAM
# or
model = whisper.load_model("small", device=DEVICE)   # ~500MB VRAM
# or
model = whisper.load_model("base", device=DEVICE)    # ~300MB VRAM
```

### Running on Different Host

Make server accessible from other machines:
```python
app.run(host='0.0.0.0', port=5000)  # Accessible from any machine on network
```

### Docker Support

To run in Docker:
```dockerfile
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

WORKDIR /app
COPY . .

RUN apt-get update && apt-get install -y \
   wget \
   bzip2 \
   ffmpeg \
   && rm -rf /var/lib/apt/lists/*

RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh \
   && bash /tmp/miniconda.sh -b -p /opt/conda \
   && rm /tmp/miniconda.sh

ENV PATH="/opt/conda/bin:$PATH"

RUN conda env update -f environment.yml --prune

EXPOSE 5000

CMD ["conda", "run", "-n", "whisper_transcriptor", "python", "app.py"]
```

Build and run:
```bash
docker build -t whisper-server .
docker run --gpus all -p 5000:5000 whisper-server
```

## File Organization

```
whisper_transcriptor/
├── app.py                 # Main Flask application
├── setup.py              # Conda setup script
├── run.bat               # Windows startup script
├── environment.yml       # Conda environment
├── README.md             # This file
├── templates/
│   └── index.html        # Web interface
├── uploads/              # Temporary upload storage
└── outputs/              # Transcription output files
```

## Privacy & Security

- ✅ All processing is local on your machine
- ✅ Files are not sent to any external servers
- ✅ Audio/video data never leaves your computer
- ⚠️ Server is accessible on local network by default
- ⚠️ For production use, implement authentication

## Performance Tips

1. **GPU Optimization:**
   - Ensure GPU drivers are up-to-date
   - Close other GPU-intensive applications
   - Monitor GPU usage with `nvidia-smi -l 1`

2. **File Processing:**
   - Convert large videos to audio first with FFmpeg
   - Use lower bitrate audio for faster processing
   - Split very long files into chunks

3. **Parallel Processing:**
   - Adjust `max_workers` based on GPU VRAM
   - Monitor memory with `nvidia-smi`
   - 4 workers is reasonable for 6GB+ VRAM

## Troubleshooting Performance

Check GPU usage:
```bash
watch -n 1 nvidia-smi
```

Monitor process:
```bash
nvidia-smi dmon
```

## Development

### Project Structure

- Backend: Flask with Whisper integration
- Frontend: Single-page application with real-time updates
- Processing: ThreadPoolExecutor with async status polling

### Extending Functionality

To add custom features, edit `app.py`:
- Add new endpoints for different transcription options
- Implement custom post-processing
- Add speaker diarization or other Whisper parameters

## License

This project is provided as-is for local use.

## Credits

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition model
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [PyTorch](https://pytorch.org/) - Deep learning framework

## Support

For issues:
1. Check troubleshooting section above
2. Verify all prerequisites are installed
3. Check GPU memory with `nvidia-smi`
4. Review logs in console output

## Version

Current Version: 1.0.0
Last Updated: February 2026

---

Enjoy fast local transcription! 🎙️✨
