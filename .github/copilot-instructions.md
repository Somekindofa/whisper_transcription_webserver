---
applyTo: '**'
---

# Whisper Transcriptor — AI agent instructions (concise)

## At a glance ✅
- Purpose: local Whisper (faster-whisper) + Pyannote speaker diarization, FastAPI UI, SQLite queue.
- Quick commands:
  - conda env create -f environment.yml
  - conda activate whisper_transcriptor
  - python app.py   # starts dev server (prints config)
  - pytest -q      # run test suite
  - python pytorch_cuda_check.py  # verify PyTorch/CUDA
- Important files: `server/main.py`, `server/routes.py`, `server/whisper_runner.py`, `server/pyannote_client.py`, `server/merge.py`, `server/db.py`, `server/file_handler.py`.

## Key architecture & runtime facts (what an agent must know) 🔧
- Services: `app.state.whisper_service` (WhisperService) is created at startup; `pyannote_client` is intentionally lazy (set to None) and instantiated in `routes.get_services()` to avoid HF-token startup failures.
- Processing flow: upload → convert (ffmpeg) → diarize (pyannote) → transcribe (Whisper) → merge (word timestamps → speakers) → store in SQLite (`storage/transcriptions.db`). See `routes.process_single_item`.
- Whisper model and device selection: configured by env vars in `server/config.py` (WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE, WHISPER_DEVICE_INDEX). `whisper_runner.select_device()`/`select_compute_type()` encapsulate logic.
- Merge strategy: `server/merge.py` matches word start/midpoints to diarization segments with fallbacks and a 0.1s tolerance — preserve this algorithm if changing merging.
- Uploads: `server/file_handler.save_upload()` streams to `storage/uploads`, uses SHA256[:16] + extension for deduplication; allowed extensions are in that file.
- Progress & UI: realtime updates via WebSocket `/api/ws/progress/{file_id}`; DB `progress_percent` maps phases (conversion/diarization/transcription/merge).

## Developer workflows & non-obvious commands 🛠️
- Use conda environment (environment.yml). Some packages are installed via pip inside that conda env (see pip: section).
- Start server with `python app.py` (it runs uvicorn programmatically and prints chosen model/device).
- Run DB migrations: `python server/migrate_db.py` (idempotent).
- Check CUDA: `python pytorch_cuda_check.py`.
- Tests: unit tests mock pyannote by injecting fake modules into `sys.modules` (look at `tests/test_pipeline_smoke.py`). Run `pytest -q` or target single tests.

## Project-specific conventions (avoid surprises) ⚠️
- Lazy-loading pattern: heavy ML models are loaded lazily — do not instantiate Pyannote at import time. Use `request.app.state` for service access.
- Direct SQLite usage (no ORM). Use `server/db.py` helpers to mutate/query state.
- Background processing uses FastAPI `BackgroundTasks` and in-process workers (not a task queue). Keep long-running CPU/GPU calls out of request handlers.
- Tests prefer isolated, deterministic units (merge, annotation conversion). When adding tests for models, prefer monkeypatching imports rather than downloading models.

## Integration points & external deps (must verify) 🌐
- FFmpeg (in PATH) — required for `convert_to_mono_wav()`.
- HuggingFace token (`PYANNOTE_TOKEN`) — required to load `pyannote/speaker-diarization-3.1` locally.
- faster-whisper / ctranslate2 — native extensions; errors surface during model init in `WhisperService._get_model()`.

## Known issues / TODOs (called out) 🔎
- webhook support exists (`server/webhook.py`) but the router is NOT registered in `server/main.py` (so webhook endpoint is currently inactive). To enable, include the router and add tests.
- `server/webhook.py` references `config.PYANNOTE_WEBHOOK_SECRET` but `server/config.py` does not define it — add `PYANNOTE_WEBHOOK_SECRET = os.getenv('PYANNOTE_WEBHOOK_SECRET','')` to `config.py` if you enable webhooks.
- `server/processing.process_queue()` contains a TODO placeholder — background queue logic primarily lives in `routes.process_single_item()` today.

## Where to look for concrete examples (copy/paste) 📌
- Add an API endpoint → follow `server/routes.py` (use `db.create_queue_item`, `db.update_status`, broadcast via WebSocket using `active_connections`).
- Change model/device defaults → edit `server/config.py` or set env vars (WHISPER_MODEL / WHISPER_DEVICE).
- Test pyannote-related code → see `tests/test_pipeline_smoke.py` (monkeypatching `pyannote` / `huggingface_hub`).
- DB schema/migration → `server/db.py` and `server/migrate_db.py`.

---

(Kept mentoring mode & progress-capture rules unchanged — preserve pedagogy and stepwise guidance.)

Please review the "Known issues / TODOs" section — would you like me to open PRs to (1) register `webhook` router and (2) add `PYANNOTE_WEBHOOK_SECRET` to `config.py`? If anything is unclear, tell me which section to expand.
