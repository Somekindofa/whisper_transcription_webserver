import hashlib
import os
from pathlib import Path

from fastapi import UploadFile

from server import config

ALLOWED_EXTENSIONS = {
    # Audio
    ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".wma", ".opus",
    # Video
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm",
}

CHUNK_SIZE = 1024 * 1024  # 1 MB chunks for streaming


def is_allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


async def save_upload(file: UploadFile, progress_callback=None) -> tuple[str, int]:
    """
    Save uploaded file with streaming (no full RAM load).
    Optional progress_callback(bytes_written) called after each chunk.
    Returns (stored_path, size_bytes).
    """
    if not is_allowed_file(file.filename):
        raise ValueError(f"File type not allowed: {file.filename}")
    
    # Create uploads directory
    uploads_dir = config.STORAGE_DIR / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    # Streaming write with hash computation
    hasher = hashlib.sha256()
    total_bytes = 0
    temp_path = uploads_dir / ".tmp_upload"
    
    # Stream file to disk
    with open(temp_path, "wb") as f:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            f.write(chunk)
            hasher.update(chunk)
            total_bytes += len(chunk)
            if progress_callback:
                await progress_callback(total_bytes)
    
    # Generate filename from hash
    file_hash = hasher.hexdigest()[:16]
    suffix = Path(file.filename).suffix.lower()
    stored_filename = f"{file_hash}{suffix}"
    stored_path = uploads_dir / stored_filename
    
    # Rename temp file to final destination. If the destination already
    # exists we treat this as a deduplication case (file already uploaded)
    # — remove the temp file and return the existing path.
    try:
        os.rename(temp_path, stored_path)
    except FileExistsError:
        try:
            os.remove(temp_path)
        except Exception:
            pass
    return str(stored_path), total_bytes


def delete_file_safely(path: str | None) -> None:
    """Delete a file if it exists."""
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass  # Ignore deletion errors
