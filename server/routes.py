import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
import logging

from server import config, db
from server.file_handler import delete_file_safely, save_upload
from server.processing import convert_to_mono_wav
from server.merge import merge_diarization_with_transcript
from server.pyannote_client import PyannoteClient
from server.whisper_runner import WhisperService

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active WebSocket connections by file_id
active_connections: dict[int, list[WebSocket]] = {}


@router.on_event("startup")
async def startup_event() -> None:
    db.init_db()


def get_services(request: Request) -> tuple[WhisperService, PyannoteClient]:
    whisper_service = request.app.state.whisper_service
    pyannote_client = request.app.state.pyannote_client

    # Lazily instantiate PyannoteClient to avoid startup failure when HF token
    # or model download is not yet available.
    if pyannote_client is None:
        try:
            pyannote_client = PyannoteClient()
            request.app.state.pyannote_client = pyannote_client
            logger.info("PyannoteClient instantiated lazily")
        except Exception as exc:
            logger.error("Failed to initialize PyannoteClient on demand: %s", exc, exc_info=True)
            raise HTTPException(status_code=503, detail=f"Pyannote initialization failed: {exc}")

    return whisper_service, pyannote_client


@router.post("/queue")
async def queue_file(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form(...),
    speakers: int = Form(...),
):
    """Upload and queue a file for transcription."""
    try:
        # Get total file size from Content-Length header
        content_length = request.headers.get("content-length")
        total_size = int(content_length) if content_length else 0
        
        # Create queue item first (before upload completes)
        # This allows us to assign a file_id and track progress
        file_id = db.create_queue_item(
            original_name=file.filename,
            stored_path="",  # Will update after upload
            size_bytes=total_size,
            language=language,
            speakers=speakers,
        )
        
        # Mark as "uploading" in DB
        db.update_status(file_id, "uploading")
        
        # Define progress callback for streaming upload
        async def upload_progress(bytes_written: int):
            """Broadcast upload progress via WebSocket."""
            if total_size > 0:
                progress_pct = (bytes_written / total_size) * 100
            else:
                progress_pct = 0
            
            # Update DB with progress
            db.update_progress(file_id, min(progress_pct, 100))
            
            # Broadcast to connected clients
            if file_id in active_connections:
                import asyncio
                for websocket in active_connections[file_id]:
                    try:
                        asyncio.create_task(websocket.send_json({
                            "file_id": file_id,
                            "progress": min(progress_pct, 100),
                            "status": "uploading",
                            "bytes_written": bytes_written,
                            "total_bytes": total_size,
                        }))
                    except Exception:
                        pass
        
        # Save file with streaming and progress tracking
        stored_path, size_bytes = await save_upload(file, progress_callback=upload_progress)
        
        # Update queue item with final path and size
        db.update_stored_path(file_id, stored_path)
        db.update_status(file_id, "queued")
        db.update_progress(file_id, 0)  # Reset progress for processing phase
        
        return {"id": file_id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/queue")
async def list_queue():
    """List all queued/processing/completed items.

    If the DB schema is out-of-date (missing new columns) attempt to run
    migrations and retry once before returning an error — this makes the
    endpoint more robust for existing installations after upgrades.
    """
    try:
        items = db.list_queue_items()
    except Exception as exc:
        # If it's likely a missing-column / schema mismatch, try to migrate and retry
        msg = str(exc)
        if "no such column" in msg or "has no column" in msg or "database schema" in msg:
            try:
                db.init_db()
                items = db.list_queue_items()
            except Exception as exc2:
                raise HTTPException(status_code=500, detail=f"DB schema error after migration attempt: {exc2}")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to list queue: {exc}")

    # Add preview for each item
    for item in items:
        if item["transcript_text"]:
            text = item["transcript_text"]
            item["preview"] = text[:200] + "..." if len(text) > 200 else text
        else:
            item["preview"] = None

    return items


@router.delete("/queue/{file_id}")
async def delete_queue_item(file_id: int):
    """Remove a queue item and its files."""
    item = db.delete_queue_item(file_id)
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Clean up files
    delete_file_safely(item["stored_path"])
    delete_file_safely(item["audio_path"])
    
    return {"status": "deleted"}


@router.patch("/queue/{file_id}")
async def update_queue_item_options(file_id: int, payload: dict):
    """Update language and/or speakers for a queue item (per-item settings).

    Accepts JSON with `language` (str) and/or `speakers` (int).
    """
    item = db.get_queue_item_by_id(file_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    language = payload.get("language") if isinstance(payload, dict) else None
    speakers = payload.get("speakers") if isinstance(payload, dict) else None

    if speakers is not None:
        try:
            speakers = int(speakers)
        except Exception:
            raise HTTPException(status_code=400, detail="`speakers` must be an integer")
        if speakers < config.MIN_SPEAKERS or speakers > config.MAX_SPEAKERS:
            raise HTTPException(status_code=400, detail=f"`speakers` must be between {config.MIN_SPEAKERS} and {config.MAX_SPEAKERS}")

    if language is None and speakers is None:
        raise HTTPException(status_code=400, detail="No updatable fields provided")

    db.update_item_options(file_id, language=language, speakers=speakers)

    updated = db.get_queue_item_by_id(file_id)
    return updated

@router.websocket("/ws/progress/{file_id}")
async def websocket_progress(websocket: WebSocket, file_id: int):
    """WebSocket endpoint for real-time progress updates.

    Defensive: log and handle exceptions during accept/registration so a
    handshake error doesn't cause a 500 without server-side context.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        await websocket.accept()
    except Exception as exc:
        logger.exception("WebSocket accept failed for file_id=%s: %s", file_id, exc)
        # If accept fails the ASGI server will return 500 to the client.
        raise

    # Register connection
    try:
        if file_id not in active_connections:
            active_connections[file_id] = []
        active_connections[file_id].append(websocket)
        logger.info("WebSocket connected for file_id=%s (total=%d)", file_id, len(active_connections[file_id]))
    except Exception as exc:
        logger.exception("Failed to register websocket for file_id=%s: %s", file_id, exc)
        try:
            await websocket.close()
        except Exception:
            pass
        return

    try:
        while True:
            # Keep connection alive; ignore incoming messages
            msg = await websocket.receive_text()
            # Log if client sends anything (useful for debugging)
            if msg:
                logger.info("Received message from websocket (file_id=%s): %s", file_id, msg)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for file_id=%s", file_id)
        try:
            active_connections[file_id].remove(websocket)
            if not active_connections[file_id]:
                del active_connections[file_id]
        except Exception:
            pass
    except Exception as exc:
        logger.exception("Unexpected error in websocket_progress for file_id=%s: %s", file_id, exc)
        try:
            active_connections[file_id].remove(websocket)
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass


# Temporary diagnostic WebSocket used while debugging handshake failures.
@router.websocket('/ws/_diag')
async def websocket_diag(websocket: WebSocket):
    """Diagnostic WS endpoint — returns a single message then closes.

    Useful for verifying that WebSocket upgrades succeed at the server.
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        await websocket.accept()
        await websocket.send_json({'status': 'ok'})
        await websocket.close()
    except Exception as exc:
        logger.exception('websocket_diag failed')
        # Surface the error to the client during handshake
        raise


@router.get('/_ws_status')
async def ws_status():
    """Return active websocket file_ids and counts (diagnostic)."""
    return {k: len(v) for k, v in active_connections.items()}


async def process_single_item(file_id: int, whisper_service: WhisperService, pyannote_client: PyannoteClient):
    """Process a single queue item: convert audio, diarize, transcribe, and merge."""
    import asyncio
    
    item = db.get_queue_item_by_id(file_id)
    if not item:
        return
    
    try:
        # Mark as active
        db.update_status(file_id, "active")
        db.update_progress(file_id, 0)

        # Broadcast immediate 'active' message so clients that connected
        # pre-emptively (on Transcribe click) will show the progress bar.
        if file_id in active_connections:
            import asyncio
            for websocket in active_connections[file_id]:
                try:
                    asyncio.create_task(websocket.send_json({
                        "file_id": file_id,
                        "progress": 0,
                        "status": "active",
                        "phase": "Starting processing..."
                    }))
                except Exception:
                    pass

        # ========== PHASE 1: CONVERT VIDEO/AUDIO TO WAV ==========
        audio_dir = config.STORAGE_DIR / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / f"{file_id}.wav"
        
        def conversion_progress_callback(progress_percent: float):
            """Broadcast FFmpeg conversion progress."""
            db.update_progress(file_id, progress_percent)
            if file_id in active_connections:
                for websocket in active_connections[file_id]:
                    try:
                        asyncio.create_task(websocket.send_json({
                            "file_id": file_id,
                            "progress": progress_percent,
                            "status": "converting",
                            "phase": "Extracting audio..."
                        }))
                    except Exception:
                        pass
        
        convert_to_mono_wav(Path(item["stored_path"]), audio_path, progress_callback=conversion_progress_callback)
        db.update_audio_path(file_id, str(audio_path))

        # Start timing for diarization + transcription (used for UI elapsed time)
        import time
        processing_start = time.time()
        
        # ========== PHASE 2: SPEAKER DIARIZATION ==========
        # If speakers == 1 we skip diarization (transcription-only fast path).
        if item["speakers"] == 1:
            # Skip diarization and jump to transcription phase
            db.update_progress(file_id, 50)
            diarization_result = None
            logger.debug("Skipping diarization for file_id=%s (speakers=1)", file_id)
        else:
            db.update_progress(file_id, 5)  # Diarization starts at 5%

            def diarization_progress_callback(progress_percent: float):
                """Map pyannote progress (0-100) into overall progress and broadcast."""
                # Map diarization 0..100 -> overall 5..50
                try:
                    pct = float(progress_percent)
                except Exception:
                    pct = 0.0
                total_progress = 5 + (pct * 0.45)
                db.update_progress(file_id, total_progress)

                if file_id in active_connections:
                    for websocket in active_connections[file_id]:
                        try:
                            asyncio.create_task(websocket.send_json({
                                "file_id": file_id,
                                "progress": total_progress,
                                "status": "processing",
                                "phase": "Identifying speakers..."
                            }))
                        except Exception:
                            pass

            num_speakers = item["speakers"] if item["speakers"] > 0 else None
            # Notify that diarization started (0%)
            diarization_progress_callback(0.0)
            diarization_result = pyannote_client.diarize(
                str(audio_path),
                num_speakers=num_speakers,
                progress_callback=diarization_progress_callback,
            )
            logger.debug("Diarization result: %s", diarization_result)

            # Store diarization results
            db.update_diarization(file_id, json.dumps(diarization_result))
            logger.debug("Diarization stored in DB for file_id=%s", file_id)

        # ========== PHASE 3: SPEECH-TO-TEXT TRANSCRIPTION ==========
        db.update_progress(file_id, 50)  # Transcription starts at 50%
        
        def transcription_progress_callback(progress_percent: float):
            """Update progress in DB and broadcast via WebSocket."""
            # Map 0-100 to 50-100 range for transcription phase
            total_progress = 50 + (progress_percent * 0.5)
            db.update_progress(file_id, total_progress)
            
            # Broadcast to connected clients
            if file_id in active_connections:
                for websocket in active_connections[file_id]:
                    try:
                        asyncio.create_task(websocket.send_json({
                            "file_id": file_id,
                            "progress": total_progress,
                            "status": "processing",
                            "phase": "Transcribing audio..."
                        }))
                    except Exception:
                        pass
        
        # Run Whisper transcription with progress callback
        transcript_result = whisper_service.transcribe(
            audio_path, 
            item["language"],
            progress_callback=transcription_progress_callback
        )
        logger.debug("Transcription result for file_id=%s: %s", file_id, transcript_result)
        
        # ========== PHASE 4: MERGE RESULTS ==========
        db.update_progress(file_id, 95)
        
        # Broadcast merging status
        if file_id in active_connections:
            for websocket in active_connections[file_id]:
                try:
                    asyncio.create_task(websocket.send_json({
                        "file_id": file_id,
                        "progress": 95,
                        "status": "processing",
                        "phase": "Finalizing results..."
                    }))
                except Exception:
                    pass
        
        # Merge diarization with transcript
        merged_text = merge_diarization_with_transcript(diarization_result, transcript_result)
        logger.debug("Merged transcript (file_id=%s): %s", file_id, merged_text)
        
        # Record processing elapsed time (diarization + transcription)
        try:
            import time
            elapsed_seconds = max(0.0, time.time() - processing_start)
            db.update_processing_time(file_id, elapsed_seconds)
        except Exception:
            logger.exception("Failed to record processing elapsed time for file_id=%s", file_id)

        # Store final results
        db.update_transcript(file_id, merged_text, transcript_result["device"])
        db.update_progress(file_id, 100)
        db.update_status(file_id, "complete")
        
        # Final completion notification
        if file_id in active_connections:
            for websocket in active_connections[file_id]:
                try:
                    asyncio.create_task(websocket.send_json({
                        "file_id": file_id,
                        "progress": 100,
                        "status": "complete",
                        "processing_seconds": elapsed_seconds
                    }))
                except Exception as e:
                    logger.warning("Failed to send completion message: %s", e)

        # Duplicate transcription/merge block removed — transcription already handled above
        # (This fixed a NameError where `progress_callback` was referenced but undefined.)
        
    except Exception as e:
        logger.exception("ERROR in process_single_item (file_id=%s): %s", file_id, e)
        import traceback
        error_details = f"{type(e).__name__}: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        db.update_status(file_id, "error", error_details)
        
        # Broadcast error
        if file_id in active_connections:
            import asyncio
            for websocket in active_connections[file_id]:
                try:
                    asyncio.create_task(websocket.send_json({
                        "file_id": file_id,
                        "status": "error",
                        "error": str(e)
                    }))
                except Exception as ex:
                    logger.warning("Failed to send error message via websocket: %s", ex)


@router.post("/transcribe")
async def start_transcription(request: Request, background_tasks: BackgroundTasks):
    """Trigger processing of all queued items."""
    whisper_service, pyannote_client = get_services(request)
    
    # Get all queued items
    items = db.get_queued_items()
    
    if not items:
        return {"status": "no_items", "count": 0}
    
    # Process each item in background
    for item in items:
        background_tasks.add_task(
            process_single_item,
            item["id"],
            whisper_service,
            pyannote_client,
        )
    
    return {"status": "started", "count": len(items)}


@router.get("/download/{file_id}")
async def download_transcript(file_id: int):
    """Download transcript as plain text."""
    item = db.get_queue_item_by_id(file_id)
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if not item["transcript_text"]:
        raise HTTPException(status_code=404, detail="Transcript not available")
    
    filename = f"{Path(item['original_name']).stem}_transcript.txt"
    
    return PlainTextResponse(
        content=item["transcript_text"],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
