def update_stored_path(file_id: int, stored_path: str) -> None:
    """Update the stored_path for a file."""
    with get_conn() as conn:
        conn.execute("UPDATE files SET stored_path = ? WHERE id = ?", (stored_path, file_id))
        conn.commit()
import sqlite3
from contextlib import contextmanager

from server import config

# Migration logic: call migrate_db.py if needed
import os
def run_migrations():
    """Run umbrella migration script if present."""
    migrate_path = os.path.join(os.path.dirname(__file__), "migrate_db.py")
    if os.path.exists(migrate_path):
        import subprocess
        subprocess.run([config.PYTHON_PATH if hasattr(config, 'PYTHON_PATH') else 'python', migrate_path], check=True)

    # Optionally, add more migration hooks here


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_name TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    audio_path TEXT,
    size_bytes INTEGER NOT NULL,
    language TEXT NOT NULL,
    speakers INTEGER NOT NULL,
    status TEXT NOT NULL,
    queued_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    pyannote_job_id TEXT,
    diarization_json TEXT,
    transcript_text TEXT,
    error_message TEXT,
    device_used TEXT,
    processing_seconds REAL DEFAULT 0,
    progress_percent REAL DEFAULT 0
);
"""


def init_db() -> None:
    config.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    # Ensure baseline schema exists
    with sqlite3.connect(config.DB_PATH) as conn:
        conn.executescript(SCHEMA_SQL)

    # Run any incremental migrations (idempotent)
    try:
        run_migrations()
    except Exception:
        # Non-fatal on environments where migrations fail; caller will
        # still have the baseline schema available. Log at debug level.
        import logging

        logging.getLogger(__name__).debug("run_migrations() failed or was a no-op")


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def create_queue_item(
    original_name: str,
    stored_path: str,
    size_bytes: int,
    language: str,
    speakers: int,
) -> int:
    """Insert a new file into the queue."""
    from datetime import datetime
    
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO files (original_name, stored_path, size_bytes, language, speakers, status, queued_at)
            VALUES (?, ?, ?, ?, ?, 'queued', ?)
            """,
            (original_name, stored_path, size_bytes, language, speakers, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return cursor.lastrowid


def list_queue_items():
    """Return all queue items ordered by status and size."""
    with get_conn() as conn:
        cursor = conn.execute(
            """
            SELECT id, original_name, size_bytes, language, speakers, status, 
                   transcript_text, error_message, processing_seconds
            FROM files
            ORDER BY 
                CASE status
                    WHEN 'active' THEN 1
                    WHEN 'queued' THEN 2
                    WHEN 'complete' THEN 3
                    WHEN 'error' THEN 4
                END,
                size_bytes ASC
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def get_queue_item_by_id(file_id: int):
    """Retrieve a single queue item by ID."""
    with get_conn() as conn:
        cursor = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_status(file_id: int, status: str, error_message: str | None = None) -> None:
    """Update the status of a queue item."""
    from datetime import datetime
    
    updates = {"status": status}
    if status == "active":
        updates["started_at"] = datetime.utcnow().isoformat()
    elif status in ("complete", "error"):
        updates["finished_at"] = datetime.utcnow().isoformat()
    
    if error_message:
        updates["error_message"] = error_message
    
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [file_id]
    
    with get_conn() as conn:
        conn.execute(f"UPDATE files SET {set_clause} WHERE id = ?", values)
        conn.commit()


def update_audio_path(file_id: int, audio_path: str) -> None:
    """Store the converted audio path."""
    with get_conn() as conn:
        conn.execute("UPDATE files SET audio_path = ? WHERE id = ?", (audio_path, file_id))
        conn.commit()


def update_pyannote_job(file_id: int, job_id: str) -> None:
    """Store the pyannote job ID."""
    with get_conn() as conn:
        conn.execute("UPDATE files SET pyannote_job_id = ? WHERE id = ?", (job_id, file_id))
        conn.commit()


def update_diarization(file_id: int, diarization_json: str) -> None:
    """Store diarization results."""
    with get_conn() as conn:
        conn.execute("UPDATE files SET diarization_json = ? WHERE id = ?", (diarization_json, file_id))
        conn.commit()


def update_processing_time(file_id: int, seconds: float) -> None:
    """Store processing elapsed time (seconds) for diarization+transcription."""
    with get_conn() as conn:
        conn.execute("UPDATE files SET processing_seconds = ? WHERE id = ?", (seconds, file_id))
        conn.commit()


def update_transcript(file_id: int, transcript_text: str, device_used: str) -> None:
    """Store final transcript and device used."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE files SET transcript_text = ?, device_used = ? WHERE id = ?",
            (transcript_text, device_used, file_id),
        )
        conn.commit()


def delete_queue_item(file_id: int) -> dict | None:
    """Delete a queue item and return its file paths for cleanup."""
    item = get_queue_item_by_id(file_id)
    if item:
        with get_conn() as conn:
            conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
            conn.commit()
    return item


def get_queued_items():
    """Get all items with 'queued' status."""
    with get_conn() as conn:
        cursor = conn.execute(
            "SELECT * FROM files WHERE status = 'queued' ORDER BY size_bytes ASC"
        )
        return [dict(row) for row in cursor.fetchall()]


def get_item_by_job_id(job_id: str):
    """Find item by pyannote job ID."""
    with get_conn() as conn:
        cursor = conn.execute("SELECT * FROM files WHERE pyannote_job_id = ?", (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_progress(file_id: int, progress_percent: float) -> None:
    """Update progress percentage (0-100) for a transcription."""
    with get_conn() as conn:
        conn.execute("UPDATE files SET progress_percent = ? WHERE id = ?", (progress_percent, file_id))
        conn.commit()


def update_item_options(file_id: int, language: str | None = None, speakers: int | None = None) -> None:
    """Update language and/or speakers for a queue item."""
    if language is None and speakers is None:
        return

    fields = []
    values = []
    if language is not None:
        fields.append("language = ?")
        values.append(language)
    if speakers is not None:
        fields.append("speakers = ?")
        values.append(speakers)

    values.append(file_id)
    set_clause = ", ".join(fields)

    with get_conn() as conn:
        conn.execute(f"UPDATE files SET {set_clause} WHERE id = ?", tuple(values))
        conn.commit()
