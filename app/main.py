"""FastAPI app: serves the UI and the transcription API. Loads the model at startup."""

from __future__ import annotations

import asyncio
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.transcriber import Transcriber

STATIC_DIR = Path(__file__).parent / "static"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

transcriber = Transcriber(
    settings.whisper_model, settings.whisper_device, settings.whisper_compute_type
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the model in a background thread so startup and /api/health stay responsive."""
    asyncio.get_event_loop().run_in_executor(None, transcriber.load)
    yield


app = FastAPI(title="Voice Notepad", lifespan=lifespan)


@app.get("/")
async def index() -> FileResponse:
    """Serve the single-file UI."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> JSONResponse:
    """Report whether the model is loaded yet, plus the active model and device."""
    return JSONResponse(
        {
            "status": "ok" if transcriber.ready else "loading",
            "model": transcriber.model_name,
            "device": transcriber.device,
        }
    )


@app.post("/api/transcribe")
async def transcribe(
    audio: UploadFile | None = None,
    language: str = Form(default=settings.default_language),
) -> JSONResponse:
    """Transcribe an uploaded audio clip to text."""
    if not transcriber.ready:
        raise HTTPException(status_code=503, detail="Model is still loading, try again shortly.")
    if audio is None or not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file was provided.")
    if language not in ("auto", "pl", "en"):
        raise HTTPException(status_code=400, detail=f"Unsupported language: {language!r}")

    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="The audio file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Audio file is too large (50 MB limit).")

    suffix = Path(audio.filename).suffix or ".webm"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(data)
        tmp.close()
        result = await run_in_threadpool(transcriber.transcribe, tmp.name, language)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - surface any decode/model error as 500
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc
    finally:
        os.unlink(tmp.name)

    return JSONResponse(
        {
            "text": result.text,
            "language": result.language,
            "duration_s": result.duration_s,
            "processing_s": result.processing_s,
        }
    )
