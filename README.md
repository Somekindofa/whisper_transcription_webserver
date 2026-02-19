# Whisper Transcriptor

**Fully local** audio/video transcription with speaker diarization using Whisper and Pyannote.audio.

## Quick Install

```bash
# Windows
install.bat

# macOS/Linux
chmod +x install.sh
./install.sh
```

Then configure your HuggingFace token in `.env` and run `start.bat` (Windows) or `python app.py` (macOS/Linux).

See [SETUP.md](SETUP.md) for detailed setup instructions.

## Features

- **100% Local Processing** - No cloud APIs, all processing on your machine
- **Drag-and-drop interface** for easy file uploads
- **Speaker diarization** using Pyannote.audio pipeline
- **Local Whisper transcription** with GPU acceleration support
- **Queue management** for batch processing
- **Real-time progress tracking** with visual status indicators
- **Export transcripts** as plain text files with speaker labels

## Prerequisites

- Conda (Miniconda or Anaconda)
- FFmpeg (for audio conversion)
- CUDA-capable GPU (recommended for speed)
- HuggingFace account (free) for pyannote model access

**Note:** This project uses conda for dependency management to avoid version conflicts with PyTorch.

## Installation

### 1. Install FFmpeg

Download and install from [ffmpeg.org](https://ffmpeg.org/download.html), ensure it's in your system PATH.

### 2. Create and activate conda environment

```bash
conda env create -f environment.yml
conda activate whisper_transcriptor
```

This installs all dependencies including PyTorch with CUDA 12.1 support.

### 3. Set environment variables

Create a `.env` file or set these environment variables:

```bash
PYANNOTE_TOKEN=your_api_key_here
PYANNOTE_WEBHOOK_SECRET=your_webhook_secret_here
WHISPER_MODEL=large-v3
WHISPER_DEVICE=auto  # auto, cuda, or cpu
WHISPER_COMPUTE_TYPE=auto  # auto, float16, int8
HOST=127.0.0.1
PORT=8000
```

Get your Pyannote.ai API key from [pyannote.ai](https://pyannote.ai).

## Usage

### Start the server

```bash
python app.py
```

```bash
conda activate whisper_transcriptor
python app.py
```

Open your browser to `http://127.0.0.1:8000`

---

### Run as a background service (Windows + Tailscale) 🟢

If you want the server to "fire-and-forget" on a Windows workstation and be reachable by other machines on your Tailscale mesh (e.g. `100.67.71.101:8000`), use a Scheduled Task or NSSM. This repo includes helper scripts in `scripts/`.

Recommended (no extra installs): create a Scheduled Task that runs at system startup (runs as SYSTEM).

1) From an elevated PowerShell prompt (Administrator) run:

```powershell
# create/start the task (adjust -PythonExe if needed)
.\scripts\install-windows-schtask.ps1 -PythonExe "C:\Path\To\python.exe" -Host 0.0.0.0 -Port 8000 -AddFirewallRule
```

2) Verify it's running and view logs:

```powershell
# view scheduled tasks
schtasks /Query /TN "WhisperTranscriptor"
# check runtime logs
Get-Content storage\\server.out.log -Tail 100 -Wait  # stdout
Get-Content storage\\server.err.log -Tail 100 -Wait  # stderr
```

3) Your team can open in their browser using the Tailscale IP and port:

```
http://100.67.71.101:8000
```

Notes and alternatives:
- The helper script launches `scripts/run_server.ps1` which sets `HOST`/`PORT` for the process and writes `storage\server.out.log` (stdout) and `storage\server.err.log` (stderr).
- If you prefer a true Windows Service, install NSSM (https://nssm.cc/) and point it at your Python executable and `app.py`.
- Keep `HOST=0.0.0.0` so the app binds the Tailscale interface; the repo default remains `127.0.0.1` so you must set HOST via `.env` or Scheduled Task args.
- For firewall access, `-AddFirewallRule` in the installer will add a rule for the selected port.

To remove the auto-start task:

```powershell
.\scripts\uninstall-windows-schtask.ps1 -RemoveFirewallRule
```

---

### Remote deploy & auto-restart 🔁

Yes — you can push a merge from another machine and have the server pull and restart automatically. Recommended approaches (pick one):

1) Push-to-deploy (direct SSH push) — best for teams inside the same Tailscale mesh
   - Create a **bare** repo on the server and add a `post-receive` hook that checks out the working tree and calls `scripts/deploy_and_restart.ps1`.
   - Developers push directly to the server (`git remote add prod ssh://user@100.67.71.101/C:/repos/whisper_transcriptor.git && git push prod master`) and the hook updates the running app.

2) CI-based deploy (recommended if you use GitHub) — use a GitHub Action that connects to the server via SSH and runs `scripts/deploy_and_restart.ps1`.
   - Example workflow added at `.github/workflows/deploy.yml` (requires an SSH key or a self-hosted runner).
   - Note: if your server is only reachable on Tailscale, prefer a self-hosted runner on that machine or use the push-to-deploy approach.

3) Poller on the server (simple, no external infra)
   - Add a Scheduled Task that runs `scripts/deploy_and_restart.ps1` periodically (e.g. every 5 minutes). The script will `git fetch`/`reset` and restart if `origin/master` changed.

What I added for you
- `scripts/restart-server.ps1` — safely stops existing `app.py` process and starts a new background instance.
- `scripts/deploy_and_restart.ps1` — `git pull` (reset to origin/branch), optional pip install, then restarts via `restart-server.ps1`.
- `.github/workflows/deploy.yml` — example GitHub Actions deployment job.

Quick manual deploy (from any machine with SSH access to the host):

```bash
ssh user@100.67.71.101 "cd 'C:\Users\dupon\Documents\Personal\whisper_transcriptor' && git pull origin master && powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\deploy_and_restart.ps1 -Branch master"
```

Security notes
- Use SSH keys and limited accounts for push-to-deploy or CI SSH.
- If you expose a deployment endpoint, require a secret and restrict access (the repo is currently only reachable inside your Tailscale mesh, which reduces exposure).

---


### Using the interface

1. **Upload files**: Drag and drop audio/video files or click to browse
2. **Configure**: Per-file language and speaker count (entered per queued item). Defaults: `fr` (French) and `1` (transcription-only).
3. **Queue**: Files are added to the queue (blue background)
4. **Transcribe**: Click "Transcribe" to start batch processing
5. **Monitor**: Active file shows yellow background with spinner
6. **Preview**: Completed files (green) show preview text
7. **Download**: Click "Download" to save full transcript
8. **Remove**: Click "Remove" to delete queued or completed items

### Status colors

- **Blue (20% opacity)**: Queued, waiting to process
- **Yellow**: Currently processing (diarization + transcription)
- **Green**: Complete, transcript available
- **Red**: Error occurred

## Supported formats

**Audio**: MP3, WAV, M4A, AAC, OGG, FLAC, WMA, OPUS
**Video**: MP4, AVI, MKV, MOV, WMV, FLV, WEBM

Video files are automatically converted to mono audio for processing.

## Architecture

1. Files uploaded via FastAPI backend
2. Audio extracted/converted using FFmpeg
3. Uploaded to Pyannote.ai for speaker diarization
4. Webhook triggers local Whisper transcription (CUDA-accelerated)
5. Results merged into speaker-attributed transcript
6. Stored in SQLite database

## Development

### Project structure

```
whisper_transcriptor/
├── app.py                 # Entry point
├── server/
│   ├── main.py           # FastAPI app
│   ├── config.py         # Configuration
│   ├── routes.py         # API endpoints
│   ├── webhook.py        # Webhook handler
│   ├── db.py             # Database operations
│   ├── models.py         # Data models
│   ├── whisper_runner.py # Whisper service
│   ├── pyannote_client.py # Pyannote API client
│   ├── processing.py     # Audio processing
│   ├── file_handler.py   # File management
│   ├── merge.py          # Diarization merge logic
│   └── web/static/       # Frontend files
│       ├── index.html
│       ├── app.js
│       └── styles.css
└── storage/              # Created at runtime
    ├── uploads/          # Original files
    ├── audio/            # Converted audio
    └── transcriptions.db # SQLite database
```

## Troubleshooting

**FFmpeg not found**: Ensure FFmpeg is installed and in your PATH

**CUDA errors**: Check CUDA installation or set `WHISPER_DEVICE=cpu`

**Webhook not working**: Ensure `PYANNOTE_WEBHOOK_SECRET` is set and matches your Pyannote.ai dashboard

**Slow transcription**: Use CUDA acceleration or reduce model size (e.g., `WHISPER_MODEL=medium`)

## License

MIT
