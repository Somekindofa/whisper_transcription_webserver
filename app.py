#!/usr/bin/env python3
"""
Whisper Transcription Webserver
A local webserver for easy audio and video transcription using OpenAI's Whisper v3 large model with CUDA acceleration.
"""

import os
import json
import asyncio
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import whisper
import torch
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid
from datetime import datetime
import logging
import sqlite3
from typing import List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = Path("uploads")
OUTPUT_FOLDER = Path("outputs")
DB_PATH = Path("transcriptions.db")
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'flac', 'ogg', 'm4a'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)


def init_db():
    """Initialize SQLite database and base schema."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transcriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE,
                filename TEXT,
                file_path TEXT,
                status TEXT,
                state TEXT,
                is_video INTEGER,
                file_size_bytes INTEGER,
                duration_seconds REAL,
                user_notes TEXT,
                created_at TEXT,
                updated_at TEXT,
                language TEXT,
                transcription TEXT,
                error TEXT
            )
            """
        )
        existing_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(transcriptions)").fetchall()
        }
        columns_to_add = {
            "file_size_bytes": "INTEGER",
            "duration_seconds": "REAL",
            "user_notes": "TEXT",
        }
        for column_name, column_type in columns_to_add.items():
            if column_name not in existing_columns:
                conn.execute(
                    f"ALTER TABLE transcriptions ADD COLUMN {column_name} {column_type}"
                )
        conn.commit()


def db_execute(query, params=()):
    """Execute a write query against SQLite."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(query, params)
        conn.commit()


def db_fetch(query, params=()):
    """Fetch rows from SQLite as dicts."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def get_job_from_db(job_id):
    """Get a single job from SQLite by job_id."""
    rows = db_fetch(
        """
        SELECT job_id, filename, status, state, file_size_bytes,
               duration_seconds, language, transcription, error, created_at, updated_at
        FROM transcriptions
        WHERE job_id = ?
        """,
        (job_id,),
    )
    return rows[0] if rows else None


def map_state(status):
    """Map internal status to requested transcription state."""
    if status in {"queued", "processing", "extracting_audio", "transcribing"}:
        return "running"
    if status == "completed":
        return "done"
    if status == "failed":
        return "error"
    if status == "deleted":
        return "deleted"
    return "running"


def set_job_status(job_id, status, *, error=None, language=None, transcription=None):
    """Update in-memory state, log transition, and persist to SQLite."""
    job_data = processing_state[job_id]
    job_data["status"] = status
    if error is not None:
        job_data["error"] = error
    if language is not None:
        job_data["language"] = language
    if transcription is not None:
        job_data["transcription"] = transcription

    state = map_state(status)
    job_data["state"] = state
    logger.info(
        "Job %s status=%s state=%s file=%s",
        job_id,
        status,
        state,
        job_data.get("filename"),
    )

    db_execute(
        """
        INSERT INTO transcriptions (
            job_id, filename, file_path, status, state, is_video,
            file_size_bytes, duration_seconds, user_notes,
            created_at, updated_at, language, transcription, error
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
            status=excluded.status,
            state=excluded.state,
            updated_at=excluded.updated_at,
            language=excluded.language,
            transcription=excluded.transcription,
            error=excluded.error
        """,
        (
            job_data.get("job_id"),
            job_data.get("filename"),
            job_data.get("file_path"),
            job_data.get("status"),
            state,
            1 if job_data.get("is_video") else 0,
            job_data.get("file_size_bytes"),
            job_data.get("duration_seconds"),
            job_data.get("user_notes"),
            job_data.get("created_at"),
            datetime.now().isoformat(),
            job_data.get("language"),
            job_data.get("transcription"),
            job_data.get("error"),
        ),
    )

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Initialize database
init_db()

# Device configuration
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {DEVICE}")

# Global processing state
processing_state = {}
executor = ThreadPoolExecutor(max_workers=4)

# Load model globally to avoid reloading
logger.info("Loading Whisper v3 large model...")
try:
    model = whisper.load_model("large-v3", device=DEVICE)
    logger.info("Whisper model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load Whisper model: {e}")
    model = None

# Diarization pipeline (lazy loaded)
DIARIZATION_PIPELINE = None
DIARIZATION_INIT_ERROR = None


def allowed_file(filename):
    """Check if file extension is allowed."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in (ALLOWED_AUDIO_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS)


def extract_audio_from_video(video_path):
    """Extract audio from MP4 or other video files using ffmpeg."""
    try:
        audio_path = UPLOAD_FOLDER / f"{uuid.uuid4()}.mp3"
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-q:a', '0',
            '-map', 'a',
            '-y',  # Overwrite output file
            str(audio_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        logger.info(f"Audio extracted from video: {video_path} -> {audio_path}")
        return audio_path
    except subprocess.TimeoutExpired:
        logger.error(f"FFmpeg timeout extracting audio from {video_path}")
        raise Exception("Video processing timeout")
    except Exception as e:
        logger.error(f"Error extracting audio from video: {e}")
        raise Exception(f"Failed to extract audio from video: {str(e)}")


def get_media_duration_seconds(file_path):
    """Get media duration in seconds using ffprobe; return None on failure."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        value = result.stdout.strip()
        return float(value) if value else None
    except Exception:
        return None


def load_diarization_pipeline():
    """Lazy-load the diarization pipeline if available."""
    global DIARIZATION_PIPELINE, DIARIZATION_INIT_ERROR
    if DIARIZATION_PIPELINE is not None or DIARIZATION_INIT_ERROR is not None:
        return

    try:
        from pyannote.audio import Pipeline
    except Exception as e:
        DIARIZATION_INIT_ERROR = f"pyannote.audio not installed: {e}"
        return

    token = os.getenv("PYANNOTE_TOKEN")
    if not token:
        DIARIZATION_INIT_ERROR = "PYANNOTE_TOKEN not set"
        return

    try:
        DIARIZATION_PIPELINE = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=token,
        )
    except Exception as e:
        DIARIZATION_INIT_ERROR = f"Failed to load diarization pipeline: {e}"


def diarize_audio(audio_path: Path, num_speakers: int) -> List[Tuple[float, float, str]]:
    """Run speaker diarization and return list of (start, end, speaker) segments."""
    if num_speakers < 1 or num_speakers > 5:
        raise ValueError("Number of speakers must be between 1 and 5")

    load_diarization_pipeline()
    if DIARIZATION_INIT_ERROR:
        raise RuntimeError(DIARIZATION_INIT_ERROR)
    if DIARIZATION_PIPELINE is None:
        raise RuntimeError("Diarization pipeline not available")

    diarization = DIARIZATION_PIPELINE(str(audio_path), num_speakers=num_speakers)
    segments: List[Tuple[float, float, str]] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append((float(turn.start), float(turn.end), str(speaker)))
    return segments


def assign_speakers_to_segments(
    whisper_segments: List[dict],
    diarization_segments: List[Tuple[float, float, str]],
) -> List[Tuple[str, float, float, str]]:
    """Match Whisper segments to diarization segments by max overlap."""
    assigned: List[Tuple[str, float, float, str]] = []
    for segment in whisper_segments:
        start = float(segment.get("start", 0))
        end = float(segment.get("end", 0))
        best_speaker = "SPEAKER_00"
        best_overlap = 0.0
        for d_start, d_end, speaker in diarization_segments:
            overlap = max(0.0, min(end, d_end) - max(start, d_start))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = speaker
        assigned.append((best_speaker, start, end, segment.get("text", "").strip()))
    return assigned


def format_diarized_transcript(
    assigned_segments: List[Tuple[str, float, float, str]]
) -> str:
    """Format diarized segments into a readable transcript."""
    lines = []
    for speaker, start, end, text in assigned_segments:
        if not text:
            continue
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines).strip()


def transcribe_audio(
    audio_path,
    job_id,
    language_hint=None,
    callback=None,
    diarization_enabled: bool = False,
    diarization_speakers: Optional[int] = None,
):
    """Transcribe audio file using Whisper."""
    try:
        if model is None:
            raise Exception("Whisper model not loaded")
        
        logger.info(f"Starting transcription for job {job_id}: {audio_path}")
        
        # Transcribe using Whisper
        transcribe_args = {"fp16": (DEVICE == "cuda")}
        if language_hint:
            transcribe_args["language"] = language_hint
        result = model.transcribe(str(audio_path), **transcribe_args)
        
        # Extract text
        transcription_text = result['text'].strip()

        # Optional diarization
        if diarization_enabled:
            if diarization_speakers is None:
                raise ValueError("Diarization enabled but no speaker count provided")
            diarization_segments = diarize_audio(Path(audio_path), diarization_speakers)
            assigned_segments = assign_speakers_to_segments(
                result.get("segments", []),
                diarization_segments,
            )
            transcription_text = format_diarized_transcript(assigned_segments)
        
        # Save results
        resolved_language = language_hint or result.get('language', 'unknown')
        set_job_status(
            job_id,
            'completed',
            language=resolved_language,
            transcription=transcription_text,
        )
        
        logger.info(f"Transcription completed for job {job_id}")
        
        if callback:
            callback(job_id, 'completed')
        
        return transcription_text
    
    except Exception as e:
        logger.error(f"Transcription error for job {job_id}: {e}")
        set_job_status(job_id, 'failed', error=str(e))
        
        if callback:
            callback(job_id, 'failed')
        
        raise


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Handle file uploads."""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    user_notes = request.form.get('notes')
    job_ids = []
    job_files = []
    
    for file in files:
        if file.filename == '':
            continue
        
        if not allowed_file(file.filename):
            continue
        
        # Create unique job ID
        job_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        file_path = UPLOAD_FOLDER / filename
        
        # Save uploaded file
        file.save(str(file_path))
        logger.info("Uploaded file %s for job %s", filename, job_id)

        file_size_bytes = file_path.stat().st_size
        duration_seconds = get_media_duration_seconds(file_path)
        
        # Determine file type
        ext = filename.rsplit('.', 1)[1].lower()
        is_video = ext in ALLOWED_VIDEO_EXTENSIONS
        
        # Initialize job state
        processing_state[job_id] = {
            'job_id': job_id,
            'filename': filename,
            'file_path': str(file_path),
            'status': 'queued',
            'state': 'running',
            'is_video': is_video,
            'file_size_bytes': file_size_bytes,
            'duration_seconds': duration_seconds,
            'user_notes': user_notes,
            'language_hint': None,
            'diarization_enabled': False,
            'diarization_speakers': None,
            'progress': 0,
            'transcription': None,
            'language': None,
            'error': None,
            'created_at': datetime.now().isoformat()
        }

        # Persist initial job row
        set_job_status(job_id, 'queued')
        
        job_ids.append(job_id)
        job_files.append({"job_id": job_id, "filename": filename})
        
    
    return jsonify({
        'job_ids': job_ids,
        'files': job_files,
        'message': f'Uploaded {len(job_ids)} file(s)'
    }), 202


@app.route('/api/process', methods=['POST'])
def process_jobs():
    """Start processing for queued jobs with optional language hint."""
    payload = request.json or {}
    job_ids = payload.get('job_ids', [])
    language = payload.get('language')
    diarization = payload.get('diarization') or {}
    diarization_enabled = bool(diarization.get('enabled'))
    diarization_speakers = diarization.get('speakers')

    if diarization_enabled:
        try:
            diarization_speakers = int(diarization_speakers)
        except (TypeError, ValueError):
            return jsonify({'error': 'Diarization speaker count must be an integer'}), 400
        if diarization_speakers < 1 or diarization_speakers > 5:
            return jsonify({'error': 'Diarization speaker count must be between 1 and 5'}), 400

    started = []

    for job_id in job_ids:
        if job_id not in processing_state:
            continue

        job_data = processing_state[job_id]
        if job_data.get('status') != 'queued':
            continue

        job_data['language_hint'] = language or None
        job_data['diarization_enabled'] = diarization_enabled
        job_data['diarization_speakers'] = diarization_speakers if diarization_enabled else None
        executor.submit(process_job, job_id)
        started.append(job_id)

    return jsonify({'started': started}), 202


def process_job(job_id):
    """Process a single transcription job."""
    try:
        job_data = processing_state[job_id]
        file_path = Path(job_data['file_path'])
        
        # Update status
        set_job_status(job_id, 'processing')
        
        # Extract audio from video if needed
        if job_data['is_video']:
            set_job_status(job_id, 'extracting_audio')
            audio_path = extract_audio_from_video(file_path)
        else:
            audio_path = file_path
        
        # Transcribe audio
        set_job_status(job_id, 'transcribing')
        transcribe_audio(
            audio_path,
            job_id,
            language_hint=job_data.get('language_hint'),
            diarization_enabled=job_data.get('diarization_enabled', False),
            diarization_speakers=job_data.get('diarization_speakers'),
        )
        
        # Clean up temporary files
        if job_data['is_video'] and audio_path != file_path:
            try:
                Path(audio_path).unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup audio file: {e}")
        
    except Exception as e:
        logger.error(f"Job processing failed for {job_id}: {e}")
        set_job_status(job_id, 'failed', error=str(e))


@app.route('/api/status/<job_id>')
def get_status(job_id):
    """Get the status of a transcription job."""
    if job_id not in processing_state:
        job_data = get_job_from_db(job_id)
        if not job_data:
            return jsonify({'error': 'Job not found'}), 404

        return jsonify({
            'job_id': job_id,
            'status': job_data.get('status'),
            'state': job_data.get('state'),
            'filename': job_data.get('filename'),
            'file_size_bytes': job_data.get('file_size_bytes'),
            'duration_seconds': job_data.get('duration_seconds'),
            'progress': 0,
            'transcription': job_data.get('transcription'),
            'language': job_data.get('language'),
            'error': job_data.get('error')
        })
    
    job_data = processing_state[job_id]
    return jsonify({
        'job_id': job_id,
        'status': job_data['status'],
        'state': job_data.get('state'),
        'filename': job_data['filename'],
        'file_size_bytes': job_data.get('file_size_bytes'),
        'duration_seconds': job_data.get('duration_seconds'),
        'progress': job_data['progress'],
        'transcription': job_data.get('transcription'),
        'language': job_data.get('language'),
        'error': job_data.get('error')
    })


@app.route('/api/download/<job_id>')
def download_transcription(job_id):
    """Download transcription as a text file."""
    if job_id not in processing_state:
        job_data = get_job_from_db(job_id)
        if not job_data:
            return jsonify({'error': 'Job not found'}), 404
        if job_data.get('status') != 'completed':
            return jsonify({'error': 'Transcription not completed'}), 400
        if not job_data.get('transcription'):
            return jsonify({'error': 'Transcription not available'}), 400

        original_name = Path(job_data['filename']).stem
        output_filename = f"{original_name}_transcription.txt"
        output_path = OUTPUT_FOLDER / output_filename

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Transcription of: {job_data['filename']}\n")
            f.write(f"Language: {job_data.get('language', 'unknown')}\n")
            f.write(f"Generated: {job_data.get('created_at', 'unknown')}\n")
            f.write("=" * 80 + "\n\n")
            f.write(job_data['transcription'])

        return send_file(
            str(output_path),
            as_attachment=True,
            download_name=output_filename,
            mimetype='text/plain'
        )
    
    job_data = processing_state[job_id]
    
    if job_data['status'] != 'completed':
        return jsonify({'error': 'Transcription not completed'}), 400
    
    # Create output file
    original_name = Path(job_data['filename']).stem
    output_filename = f"{original_name}_transcription.txt"
    output_path = OUTPUT_FOLDER / output_filename
    
    # Write transcription to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"Transcription of: {job_data['filename']}\n")
        f.write(f"Language: {job_data.get('language', 'unknown')}\n")
        f.write(f"Generated: {job_data.get('created_at', 'unknown')}\n")
        f.write("=" * 80 + "\n\n")
        f.write(job_data['transcription'])
    
    return send_file(
        str(output_path),
        as_attachment=True,
        download_name=output_filename,
        mimetype='text/plain'
    )


@app.route('/api/batch-download', methods=['POST'])
def batch_download():
    """Download multiple transcriptions as a zip file."""
    import zipfile
    
    job_ids = request.json.get('job_ids', [])
    
    if not job_ids:
        return jsonify({'error': 'No job IDs provided'}), 400
    
    # Create zip file
    zip_filename = f"transcriptions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path = OUTPUT_FOLDER / zip_filename
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for job_id in job_ids:
            if job_id not in processing_state:
                continue
            
            job_data = processing_state[job_id]
            if job_data['status'] != 'completed':
                continue
            
            # Create output file
            original_name = Path(job_data['filename']).stem
            output_filename = f"{original_name}_transcription.txt"
            
            content = f"Transcription of: {job_data['filename']}\n"
            content += f"Language: {job_data.get('language', 'unknown')}\n"
            content += f"Generated: {job_data.get('created_at', 'unknown')}\n"
            content += "=" * 80 + "\n\n"
            content += job_data['transcription']
            
            zipf.writestr(output_filename, content)
    
    return send_file(
        str(zip_path),
        as_attachment=True,
        download_name=zip_filename,
        mimetype='application/zip'
    )


@app.route('/api/clear-jobs', methods=['POST'])
def clear_jobs():
    """Clear completed/failed jobs from memory."""
    job_ids = request.json.get('job_ids', [])
    
    for job_id in job_ids:
        if job_id in processing_state:
            file_path = processing_state[job_id].get('file_path')
            if file_path:
                try:
                    Path(file_path).unlink(missing_ok=True)
                except Exception as e:
                    logger.warning("Failed to delete file %s: %s", file_path, e)
            set_job_status(job_id, 'deleted')
            del processing_state[job_id]
        db_execute("DELETE FROM transcriptions WHERE job_id = ?", (job_id,))
    
    return jsonify({'message': 'Jobs cleared'})


@app.route('/api/jobs')
def list_jobs():
    """List recent jobs from SQLite."""
    limit = request.args.get('limit', 50)
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(limit, 200))

    rows = db_fetch(
        """
        SELECT job_id, filename, status, state, file_size_bytes,
               duration_seconds, language, transcription, error, created_at, updated_at
        FROM transcriptions
        WHERE status != 'deleted'
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (limit,),
    )

    return jsonify({'jobs': rows})


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error."""
    return jsonify({'error': 'File too large. Maximum size is 500MB'}), 413


if __name__ == '__main__':
    logger.info("Starting Whisper Transcription Webserver")
    logger.info(f"Upload folder: {UPLOAD_FOLDER.absolute()}")
    logger.info(f"Output folder: {OUTPUT_FOLDER.absolute()}")
    app.run(host='0.0.0.0', port=5000, debug=False)
