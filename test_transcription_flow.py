"""Test the full transcription flow to identify where WinError 127 occurs."""
import sys
import traceback
from pathlib import Path

# Test file
TEST_AUDIO = Path(r"C:\Users\dupon\Documents\Personal\whisper_transcriptor\storage\audio\23.wav")

if not TEST_AUDIO.exists():
    print(f"ERROR: Test file not found: {TEST_AUDIO}")
    sys.exit(1)

print(f"Testing with: {TEST_AUDIO}\n")

# Phase 1: Test PyannoteClient initialization
print("=" * 60)
print("PHASE 1: Initialize PyannoteClient")
print("=" * 60)
try:
    from server.pyannote_client import PyannoteClient
    pyannote_client = PyannoteClient()
    print("✓ PyannoteClient initialized successfully\n")
except Exception as e:
    print(f"✗ Failed to initialize PyannoteClient:")
    print(f"  {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)

# Phase 2: Test Diarization
print("=" * 60)
print("PHASE 2: Run Diarization")
print("=" * 60)
try:
    result = pyannote_client.diarize(str(TEST_AUDIO), num_speakers=None)
    print(f"✓ Diarization completed successfully")
    print(f"  Found {len(result['diarization'])} segments\n")
except Exception as e:
    print(f"✗ Diarization failed:")
    print(f"  {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)

# Phase 3: Test WhisperService initialization
print("=" * 60)
print("PHASE 3: Initialize WhisperService")
print("=" * 60)
try:
    from server.whisper_runner import WhisperService
    whisper_service = WhisperService()
    print("✓ WhisperService initialized successfully\n")
except Exception as e:
    print(f"✗ Failed to initialize WhisperService:")
    print(f"  {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)

# Phase 4: Test Transcription (this loads the model)
print("=" * 60)
print("PHASE 4: Run Transcription")
print("=" * 60)
try:
    transcript = whisper_service.transcribe(TEST_AUDIO, "en")
    print(f"✓ Transcription completed successfully")
    print(f"  Text preview: {transcript['preview']}\n")
except Exception as e:
    print(f"✗ Transcription failed:")
    print(f"  {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)

# Phase 5: Test Merge
print("=" * 60)
print("PHASE 5: Merge Results")
print("=" * 60)
try:
    from server.merge import merge_diarization_with_transcript
    merged = merge_diarization_with_transcript(result, transcript)
    print(f"✓ Merge completed successfully")
    print(f"  Merged text length: {len(merged)} chars\n")
except Exception as e:
    print(f"✗ Merge failed:")
    print(f"  {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)

print("=" * 60)
print("ALL TESTS PASSED ✓")
print("=" * 60)
