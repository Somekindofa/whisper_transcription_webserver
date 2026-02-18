import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BASE_DIR / "storage"))
STATIC_DIR = Path(os.getenv("STATIC_DIR", BASE_DIR / "server" / "web" / "static"))
DB_PATH = Path(os.getenv("DB_PATH", BASE_DIR / "storage" / "transcriptions.db"))

# HuggingFace token for local pyannote.audio pipeline
PYANNOTE_API_KEY = os.getenv("PYANNOTE_TOKEN", "")

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "auto")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "auto")
WHISPER_DEVICE_INDEX = os.getenv("WHISPER_DEVICE_INDEX", "")

# Secret used to verify incoming pyannote webhook signatures (optional)
PYANNOTE_WEBHOOK_SECRET = os.getenv('PYANNOTE_WEBHOOK_SECRET', '')

MAX_SPEAKERS = 5
MIN_SPEAKERS = 1

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
