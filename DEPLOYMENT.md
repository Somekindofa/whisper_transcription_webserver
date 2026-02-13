# Deployment & Advanced Configuration Guide

## Table of Contents
1. [System Setup](#system-setup)
2. [Production Deployment](#production-deployment)
3. [Performance Tuning](#performance-tuning)
4. [Docker Deployment](#docker-deployment)
5. [Network Configuration](#network-configuration)
6. [Monitoring & Logging](#monitoring--logging)

## System Setup

### Windows

#### Prerequisites Installation

**1. Conda (Miniconda/Anaconda)**
```
Download from: https://docs.conda.io/en/latest/miniconda.html
Make sure to check "Add Conda to PATH" during installation
Verify: conda --version
```

**2. FFmpeg**
```
Option A: Download from https://ffmpeg.org/download.html
Option B: Use Windows Package Manager
  winget install ffmpeg

Verify: ffmpeg -version
```

**3. NVIDIA CUDA (for GPU acceleration)**
```
1. Download CUDA Toolkit: https://developer.nvidia.com/cuda-downloads
2. Download cuDNN: https://developer.nvidia.com/cudnn
3. Follow installation instructions
4. Verify: nvidia-smi (should show GPU)
```

#### Running the Server

**Option 1: Batch file (easiest)**
```
Double-click run.bat
```

**Option 2: PowerShell**
```powershell
powershell -ExecutionPolicy Bypass -File run.ps1
```

**Option 3: Command Prompt**
```bash
conda env update -f environment.yml --prune
conda run -n whisper_transcriptor python app.py
```

### Linux

#### Prerequisites Installation

**Ubuntu/Debian:**
```bash
# Conda (Miniconda)
# Download and install from: https://docs.conda.io/en/latest/miniconda.html

# FFmpeg
sudo apt-get install ffmpeg

# NVIDIA CUDA (if you have NVIDIA GPU)
# Follow instructions from https://developer.nvidia.com/cuda-downloads
```

**CentOS/RHEL:**
```bash
# Conda (Miniconda)
# Download and install from: https://docs.conda.io/en/latest/miniconda.html

# FFmpeg
sudo yum install ffmpeg

# NVIDIA CUDA
# Follow instructions from https://developer.nvidia.com/cuda-downloads
```

#### Running the Server

```bash
conda env update -f environment.yml --prune
conda run -n whisper_transcriptor python app.py
```

### macOS

#### Prerequisites Installation

```bash
# Using Homebrew
# Install Conda separately from: https://docs.conda.io/en/latest/miniconda.html
brew install ffmpeg

# For NVIDIA GPUs (not common on Mac)
# Metal GPU acceleration will be used if available
```

#### Running the Server

```bash
conda env update -f environment.yml --prune
conda run -n whisper_transcriptor python app.py
```

## Production Deployment

### Using Gunicorn (Production WSGI Server)

**Installation:**
```bash
conda install -n whisper_transcriptor -c conda-forge gunicorn
```

**Run with Gunicorn:**
```bash
gunicorn --workers 2 --worker-class sync --bind 0.0.0.0:5000 app:app
```

**With multiple workers:**
```bash
gunicorn --workers 4 --worker-class gthread --threads 2 --bind 0.0.0.0:5000 app:app
```

### Using Nginx as Reverse Proxy

**1. Install Nginx**

**Windows:** Download from https://nginx.org/en/download.html

**Linux:**
```bash
sudo apt-get install nginx
```

**2. Nginx Configuration** (`/etc/nginx/sites-available/whisper`)

```nginx
upstream whisper_app {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name your-domain.com;
    client_max_body_size 500M;

    location / {
        proxy_pass http://whisper_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeouts for large files
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /api/upload {
        proxy_pass http://whisper_app;
        client_max_body_size 500M;
        proxy_read_timeout 600s;
    }
}
```

**3. Enable Nginx**

```bash
sudo ln -s /etc/nginx/sites-available/whisper /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Using Systemd Service (Linux)

**Create service file** (`/etc/systemd/system/whisper.service`):

```ini
[Unit]
Description=Whisper Transcription Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/www-data/whisper_transcriptor
ExecStart=/usr/bin/conda run -n whisper_transcriptor python app.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable whisper
sudo systemctl start whisper
sudo systemctl status whisper
```

## Performance Tuning

### GPU Optimization

**1. Monitor GPU Usage**
```bash
# Continuous monitoring
nvidia-smi -l 1

# Detailed monitoring
nvidia-smi dmon

# Memory profiling
nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv,noheader
```

**2. Adjust Parallel Processing**

Edit `app.py`:
```python
# Increase for more parallel processing (if GPU has enough VRAM)
executor = ThreadPoolExecutor(max_workers=8)

# Decrease for less GPU usage
executor = ThreadPoolExecutor(max_workers=2)
```

**3. Use Smaller Models for Faster Processing**

Edit `app.py`, change model loading:
```python
# Faster, lower accuracy
model = whisper.load_model("base", device=DEVICE)  # ~300MB VRAM

# Medium speed/accuracy
model = whisper.load_model("medium", device=DEVICE)  # ~1.5GB VRAM

# Slowest, highest accuracy
model = whisper.load_model("large-v3", device=DEVICE)  # ~10GB VRAM
```

**4. Optimize PyTorch Settings**

Add to `app.py` before loading model:
```python
import torch

# For better GPU performance
torch.set_num_threads(1)  # Prevent CPU bottleneck
torch.backends.cudnn.benchmark = True
torch.cuda.empty_cache()

# Load model with FP16 for faster inference
model = whisper.load_model("large-v3", device=DEVICE)
if DEVICE == "cuda":
    model = model.half()  # Convert to FP16
```

### CPU Optimization

```python
import torch
import os

# Set number of CPU threads
os.environ['OMP_NUM_THREADS'] = '8'
torch.set_num_threads(8)
```

### Memory Management

**1. Limit VRAM Usage**

```python
import torch
torch.cuda.set_per_process_memory_fraction(0.8)  # Use max 80% of VRAM
```

**2. Clear Cache Between Transcriptions**

```python
def process_job(job_id):
    try:
        # ... transcription code ...
        if DEVICE == "cuda":
            torch.cuda.empty_cache()
    finally:
        # ... cleanup ...
```

**3. Monitor Memory**

```python
import psutil

# Check system memory
memory = psutil.virtual_memory()
print(f"System RAM: {memory.used}/{memory.total} MB")

# Check GPU memory
if DEVICE == "cuda":
    import torch
    print(f"GPU VRAM: {torch.cuda.memory_allocated()/1e9:.2f}GB")
```

## Docker Deployment

### Dockerfile for GPU Support

```dockerfile
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    bzip2 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh \
    && bash /tmp/miniconda.sh -b -p /opt/conda \
    && rm /tmp/miniconda.sh

ENV PATH="/opt/conda/bin:$PATH"

# Copy application
COPY . .

# Create conda environment
RUN conda env update -f environment.yml --prune

# Create directories
RUN mkdir -p uploads outputs

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000').read()" || exit 1

# Run application
CMD ["conda", "run", "-n", "whisper_transcriptor", "python", "app.py"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  whisper:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "5000:5000"
    volumes:
      - ./uploads:/app/uploads
      - ./outputs:/app/outputs
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
```

**Run with Docker Compose:**
```bash
docker-compose up -d
```

### Docker Build and Run

```bash
# Build image
docker build -t whisper-transcriptor:latest .

# Run with GPU support
docker run --gpus all \
    -p 5000:5000 \
    -v $(pwd)/uploads:/app/uploads \
    -v $(pwd)/outputs:/app/outputs \
    whisper-transcriptor:latest

# Run on Windows (PowerShell)
docker run --gpus all `
    -p 5000:5000 `
    -v ${PWD}/uploads:/app/uploads `
    -v ${PWD}/outputs:/app/outputs `
    whisper-transcriptor:latest
```

## Network Configuration

### Accessing from Other Machines

**Current Configuration (localhost only):**
```python
app.run(host='127.0.0.1', port=5000)
```

**Network Access (local network):**
```python
app.run(host='0.0.0.0', port=5000)
```

Then access from other machines:
- From `hostname` (replace with actual): `http://hostname:5000`
- From IP address: `http://192.168.1.100:5000`

### CORS Configuration

Add CORS support to `app.py`:
```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["localhost", "127.0.0.1", "192.168.*"],
        "methods": ["GET", "POST"]
    }
})
```

Install: `conda install -n whisper_transcriptor -c conda-forge flask-cors`

### Firewall Configuration

**Windows Firewall:**
1. Control Panel → Windows Defender Firewall → Allow an app through firewall
2. Add Python (app.py)
3. Or allow port 5000

**Linux (UFW):**
```bash
sudo ufw allow 5000/tcp
sudo ufw enable
```

## Monitoring & Logging

### Enable Detailed Logging

Edit `app.py`:
```python
import logging

# Set to DEBUG for more details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('whisper_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
```

### Monitor GPU in Background

```bash
# Linux/Mac - every second
watch -n 1 nvidia-smi

# Windows - PowerShell
while($true) { Clear-Host; nvidia-smi; Start-Sleep -Seconds 1 }
```

### Performance Monitoring Script

Create `monitor.py`:
```python
import psutil
import subprocess
import json
from datetime import datetime

def get_system_stats():
    stats = {
        'timestamp': datetime.now().isoformat(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory': {
            'percent': psutil.virtual_memory().percent,
            'used_gb': psutil.virtual_memory().used / 1e9,
            'total_gb': psutil.virtual_memory().total / 1e9
        }
    }
    
    try:
        gpu_info = subprocess.check_output(
            'nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader',
            shell=True
        ).decode().strip().split(',')
        stats['gpu'] = {
            'utilization': gpu_info[0].strip(),
            'memory_used': gpu_info[1].strip(),
            'memory_total': gpu_info[2].strip()
        }
    except:
        stats['gpu'] = None
    
    return stats

if __name__ == '__main__':
    import time
    while True:
        stats = get_system_stats()
        print(json.dumps(stats, indent=2))
        time.sleep(5)
```

Run: `python monitor.py`

### Health Check Endpoint

Add to `app.py`:
```python
@app.route('/health')
def health_check():
    import torch
    return jsonify({
        'status': 'healthy',
        'device': DEVICE,
        'gpu_available': torch.cuda.is_available(),
        'jobs_processing': len([j for j in processing_state.values() if j['status'] == 'processing']),
        'jobs_completed': len([j for j in processing_state.values() if j['status'] == 'completed'])
    })
```

Access: `http://localhost:5000/health`

---

For more information, see README.md and QUICKSTART.md
