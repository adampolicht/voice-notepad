"""FastAPI app: serves the UI and the transcription API. Loads the model at startup."""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.notes import ID_RE, NotesStore
from app.transcriber import Transcriber

STATIC_DIR = Path(__file__).parent / "static"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

logger = logging.getLogger("voice_notepad")

transcriber = Transcriber(
    settings.whisper_model, settings.whisper_device, settings.whisper_compute_type
)
notes = NotesStore(settings.notes_dir)


def _load_model() -> None:
    """Load the model, logging any failure so /api/health doesn't just hang on 'loading'."""
    try:
        transcriber.load()
        logger.info("Model loaded: %s on %s", transcriber.model_name, transcriber.device)
    except Exception:
        logger.exception("Failed to load model %r", transcriber.model_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the model in a background thread so startup and /api/health stay responsive."""
    asyncio.get_running_loop().run_in_executor(None, _load_model)
    yield


app = FastAPI(title="Voice Notepad", lifespan=lifespan)


@app.get("/")
async def index() -> FileResponse:
    """Serve the single-file UI. No-cache so a rebuilt UI always loads fresh."""
    return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})


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


class NoteCreate(BaseModel):
    title: str = ""
    content: str = ""


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


def _summary(note) -> dict:
    """List payload: everything but the body, so the sidebar stays light."""
    return {k: v for k, v in asdict(note).items() if k != "content"}


def _require_id(note_id: str) -> None:
    """Reject ids that aren't our 32-char hex, before they reach the filesystem."""
    if not ID_RE.match(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id.")


@app.get("/api/notes")
async def list_notes() -> JSONResponse:
    """List all saved notes, newest first (summaries without body text)."""
    return JSONResponse([_summary(n) for n in notes.list()])


@app.post("/api/notes")
async def create_note(payload: NoteCreate) -> JSONResponse:
    """Create a new note and return it in full."""
    note = notes.create(title=payload.title, content=payload.content)
    return JSONResponse(asdict(note), status_code=201)


@app.get("/api/notes/{note_id}")
async def get_note(note_id: str) -> JSONResponse:
    """Return one note in full, including its body."""
    _require_id(note_id)
    note = notes.get(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found.")
    return JSONResponse(asdict(note))


@app.put("/api/notes/{note_id}")
async def update_note(note_id: str, payload: NoteUpdate) -> JSONResponse:
    """Update a note's content and/or title."""
    _require_id(note_id)
    note = notes.update(note_id, content=payload.content, title=payload.title)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found.")
    return JSONResponse(asdict(note))


@app.delete("/api/notes/{note_id}", status_code=204)
async def delete_note(note_id: str) -> Response:
    """Delete a note's file from disk."""
    _require_id(note_id)
    if not notes.delete(note_id):
        raise HTTPException(status_code=404, detail="Note not found.")
    return Response(status_code=204)
