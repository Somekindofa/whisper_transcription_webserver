import subprocess
from pathlib import Path

from server import config
from server.pyannote_client import PyannoteClient
from server.whisper_runner import WhisperService


def convert_to_mono_wav(input_path: Path, output_path: Path, progress_callback=None) -> None:
    """
    Convert audio/video to mono WAV for Whisper using ffmpeg.
    Optional progress_callback(progress_percent) tracks conversion progress.
    """
    # Resolve to absolute path and check if file exists
    input_path = Path(input_path).resolve()
    if not input_path.exists():
        raise RuntimeError(f"Input file does not exist: {input_path}")
    
    output_path = Path(output_path).resolve()
    
    cmd = [
        "ffmpeg",
        "-i", str(input_path),
        "-ar", "16000",  # 16 kHz sample rate
        "-ac", "1",      # mono
        "-f", "wav",
        "-y",            # overwrite output
        str(output_path),
    ]
    
    # Run with progress tracking via stderr
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line buffering
    )

    # Collect stderr output for error reporting
    stderr_lines = []
    duration_seconds = None
    try:
        for line in process.stderr:
            stderr_lines.append(line)
            # Extract total duration from FFmpeg output
            if "Duration:" in line and duration_seconds is None:
                # Parse "Duration: HH:MM:SS.ms"
                parts = line.split("Duration:")[1].split(",")[0].split(":")
                try:
                    hours = int(parts[0].strip())
                    minutes = int(parts[1].strip())
                    seconds = float(parts[2].strip())
                    duration_seconds = hours * 3600 + minutes * 60 + seconds
                except (ValueError, IndexError):
                    pass

            # Parse current time from "time=HH:MM:SS.ms"
            if "time=" in line and duration_seconds:
                try:
                    time_str = line.split("time=")[1].split()[0]
                    parts = time_str.split(":")
                    h = int(parts[0])
                    m = int(parts[1])
                    s = float(parts[2])
                    current_seconds = h * 3600 + m * 60 + s
                    progress = (current_seconds / duration_seconds) * 100
                    if progress_callback:
                        progress_callback(min(progress, 100))
                except (ValueError, IndexError):
                    pass
    finally:
        process.wait()

    if process.returncode != 0:
        error_output = ''.join(stderr_lines)
        raise RuntimeError(f"ffmpeg conversion failed.\nFFmpeg output:\n{error_output}")

    if progress_callback:
        progress_callback(100)


def order_queue_by_size(items):
    """Sort queued items from smallest to largest by size."""
    return sorted(items, key=lambda x: x["size_bytes"])


def process_queue(
    items,
    whisper_service: WhisperService,
    pyannote_client: PyannoteClient,
):
    """
    Process queue items: convert audio, submit diarization.
    Note: Whisper transcription is triggered by webhook after diarization completes.
    """
    # This function is called by the /transcribe endpoint
    # It should be run in a background task
    # TODO: Implement background processing with proper error handling
    return None
