from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from server import config
from server.pyannote_client import PyannoteClient
from server.routes import router as api_router
from server.whisper_runner import WhisperService
from server.webhook import router as webhook_router


def create_app() -> FastAPI:
    app = FastAPI(title="Whisper Transcriptor")

    # Initialize services (pyannote is lazy-loaded on first use)
    app.state.whisper_service = WhisperService()
    app.state.pyannote_client = None

    app.include_router(api_router, prefix="/api")
    # Register webhook router so external services (pyannote) can POST
    # status updates that we forward to connected clients.
    app.include_router(webhook_router, prefix="/api")

    app.mount(
        "/",
        StaticFiles(directory=config.STATIC_DIR, html=True),
        name="static",
    )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "server.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
    )
