# Configuration File for Whisper Transcription Server
# Modify this file to customize server behavior

# Server Configuration
SERVER_HOST = "0.0.0.0"          # "0.0.0.0" for network access, "127.0.0.1" for localhost only
SERVER_PORT = 5000               # Port to run the server on
DEBUG_MODE = False               # Set to True for development

# Model Configuration
WHISPER_MODEL = "large-v3"       # Options: "tiny", "base", "small", "medium", "large", "large-v3"
DEVICE = "cuda"                  # "cuda" for GPU, "cpu" for CPU (auto-detects)

# Processing Configuration
MAX_PARALLEL_WORKERS = 4         # Number of files to process in parallel
MAX_FILE_SIZE_MB = 500           # Maximum file size in megabytes
PROCESSING_TIMEOUT = 300         # Timeout in seconds per file

# File Configuration
UPLOAD_FOLDER = "uploads"        # Where to store uploaded files temporarily
OUTPUT_FOLDER = "outputs"        # Where to store transcription results
ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "flac", "ogg", "m4a"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv"}

# Feature Configuration
ENABLE_BATCH_DOWNLOAD = True     # Allow downloading multiple transcriptions as ZIP
ENABLE_VIDEO_SUPPORT = True      # Requires FFmpeg
ENABLE_LANGUAGE_DETECTION = True # Show detected language
EXTRACT_AUDIO_QUALITY = "0"      # FFmpeg audio quality (0=highest, higher=lower)

# Advanced Configuration
AUTO_CLEANUP_UPLOADS = True      # Delete uploaded files after processing
KEEP_TRANSCRIPTIONS = True       # Keep transcription text files in output folder
MAX_CONCURRENT_GPU_PROCESSES = 4 # Limit GPU usage

# Logging
LOG_LEVEL = "INFO"               # "DEBUG", "INFO", "WARNING", "ERROR"
LOG_FILE = "server.log"          # Log file name (empty to disable file logging)

# Security (for production use)
REQUIRE_API_KEY = False          # Require API key for uploads
API_KEY = "your-secret-key-here" # Only used if REQUIRE_API_KEY = True
ALLOWED_ORIGINS = ["localhost"]  # CORS allowed origins

# UI Configuration
THEME = "light"                  # "light" or "dark"
PRIMARY_COLOR = "#667eea"        # Primary color for UI
SECONDARY_COLOR = "#764ba2"      # Secondary color for UI
