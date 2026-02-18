import hashlib
import hmac
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response, status

from server import config, db
from server.merge import merge_diarization_with_transcript
from server.pyannote_client import PyannoteClient
from server.whisper_runner import WhisperService

router = APIRouter()


def verify_webhook_signature(payload: bytes, timestamp: str, signature: str) -> bool:
    """Verify pyannote webhook signature using HMAC-SHA256."""
    if not config.PYANNOTE_WEBHOOK_SECRET:
        return True  # Skip verification if no secret configured
    
    message = f"v0:{timestamp}:{payload.decode()}"
    expected_sig = hmac.new(
        config.PYANNOTE_WEBHOOK_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    
    expected_full = f"v0={expected_sig}"
    return hmac.compare_digest(expected_full, signature)


@router.post("/pyannote")
async def pyannote_webhook(request: Request) -> Response:
    """Handle pyannote webhook for diarization completion."""
    whisper_service: WhisperService = request.app.state.whisper_service
    pyannote_client: PyannoteClient = request.app.state.pyannote_client
    
    # Get raw body for signature verification
    body = await request.body()
    timestamp = request.headers.get("X-Request-Timestamp", "")
    signature = request.headers.get("X-Signature", "")
    
    if not verify_webhook_signature(body, timestamp, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse webhook payload
    payload = json.loads(body)
    job_id = payload.get("jobId")
    job_status = payload.get("status")
    output = payload.get("output")
    
    # Find the corresponding file
    item = db.get_item_by_job_id(job_id)
    if not item:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    # Support intermediate progress notifications from pyannote (if sent)
    # e.g. payload may contain {'progress': 0.42} (0..1) or {'progress': 42}
    raw_progress = payload.get('progress') or payload.get('progress_percent') or payload.get('percent')
    if raw_progress is not None:
        try:
            p = float(raw_progress)
            if p <= 1.0:
                p = p * 100.0
            p = max(0.0, min(100.0, p))
            db.update_progress(item['id'], 5 + (p * 0.45))  # map diarization into 5..50
            # broadcast diarization progress
            try:
                from server.routes import active_connections
                import asyncio
                if item['id'] in active_connections:
                    for websocket in active_connections[item['id']]:
                        try:
                            asyncio.create_task(websocket.send_json({
                                'file_id': item['id'],
                                'progress': 5 + (p * 0.45),
                                'status': 'processing',
                                'phase': 'Identifying speakers...'
                            }))
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            pass

    if job_status == "succeeded" and output:
        # Store diarization results
        db.update_diarization(item["id"], json.dumps(output))
        
        # Trigger Whisper transcription (synchronous for now)
        try:
            audio_path = Path(item["audio_path"])
            transcript_result = whisper_service.transcribe(audio_path, item["language"])
            
            # Merge diarization with transcript
            merged_text = merge_diarization_with_transcript(output, transcript_result)
            
            db.update_transcript(
                item["id"],
                merged_text,
                transcript_result["device"],
            )
            db.update_status(item["id"], "complete")

            # Broadcast completion to any connected WebSocket clients
            try:
                from server.routes import active_connections
                import asyncio

                if item["id"] in active_connections:
                    for websocket in active_connections[item["id"]]:
                        try:
                            asyncio.create_task(websocket.send_json({
                                "file_id": item["id"],
                                "progress": 100,
                                "status": "complete",
                                "phase": "Completed",
                                "processing_seconds": item.get("processing_seconds", 0),
                            }))
                        except Exception:
                            pass
            except Exception:
                # non-fatal: broadcasting is best-effort
                pass
        except Exception as e:
            db.update_status(item["id"], "error", str(e))
            try:
                from server.routes import active_connections
                import asyncio
                if item["id"] in active_connections:
                    for websocket in active_connections[item["id"]]:
                        try:
                            asyncio.create_task(websocket.send_json({
                                "file_id": item["id"],
                                "status": "error",
                                "error": str(e),
                            }))
                        except Exception:
                            pass
            except Exception:
                pass

    elif job_status == "failed":
        db.update_status(item["id"], "error", "Diarization failed")
        try:
            from server.routes import active_connections
            import asyncio
            if item["id"] in active_connections:
                for websocket in active_connections[item["id"]]:
                    try:
                        asyncio.create_task(websocket.send_json({
                            "file_id": item["id"],
                            "status": "error",
                            "error": "Diarization failed",
                        }))
                    except Exception:
                        pass
        except Exception:
            pass
    
    return Response(status_code=status.HTTP_202_ACCEPTED)
