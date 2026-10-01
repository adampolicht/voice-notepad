"""faster-whisper wrapper: load the model once, transcribe a file to text."""

from __future__ import annotations

import time
from dataclasses import dataclass

import ctranslate2
from faster_whisper import WhisperModel


def _resolve_device(device: str) -> str:
    """Resolve 'auto' to 'cuda' when a GPU is present, else 'cpu'."""
    if device != "auto":
        return device
    try:
        return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    except Exception:
        return "cpu"


def _resolve_compute_type(compute_type: str, device: str) -> str:
    """Resolve 'auto' to float16 on GPU, int8 on CPU."""
    if compute_type != "auto":
        return compute_type
    return "float16" if device == "cuda" else "int8"


@dataclass
class TranscriptionResult:
    text: str
    language: str
    duration_s: float
    processing_s: float


class Transcriber:
    """Holds a single loaded WhisperModel and transcribes audio files."""

    def __init__(self, model_name: str, device: str, compute_type: str) -> None:
        self.model_name = model_name
        self.device = _resolve_device(device)
        self.compute_type = _resolve_compute_type(compute_type, self.device)
        self._model: WhisperModel | None = None
        self.load_error: str | None = None

    def load(self) -> None:
        """Load the model into memory (downloads on first run). Records any failure."""
        try:
            self._model = WhisperModel(
                self.model_name, device=self.device, compute_type=self.compute_type
            )
        except Exception as exc:
            self.load_error = f"{type(exc).__name__}: {exc}"
            raise

    @property
    def ready(self) -> bool:
        return self._model is not None

    def transcribe(self, audio_path: str, language: str = "auto") -> TranscriptionResult:
        """Transcribe a file. `language` is 'auto', 'pl', or 'en'."""
        if self._model is None:
            raise RuntimeError("Model is not loaded")

        lang = None if language == "auto" else language
        start = time.perf_counter()
        segments, info = self._model.transcribe(
            audio_path,
            language=lang,
            vad_filter=True,
        )
        text = "".join(segment.text for segment in segments).strip()
        processing_s = time.perf_counter() - start

        return TranscriptionResult(
            text=text,
            language=info.language,
            duration_s=round(info.duration, 2),
            processing_s=round(processing_s, 2),
        )
