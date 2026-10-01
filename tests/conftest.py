"""Shared test fixtures. API tests use a fake transcriber so no model is downloaded."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import main
from app.transcriber import TranscriptionResult


class FakeTranscriber:
    """Stand-in for Transcriber with controllable readiness and a canned result."""

    def __init__(self, ready: bool = True) -> None:
        self.model_name = "fake"
        self.device = "cpu"
        self._ready = ready
        self.load_error: str | None = None
        self.last_call: tuple[str, str] | None = None

    @property
    def ready(self) -> bool:
        return self._ready

    def load(self) -> None:
        self._ready = True

    def transcribe(self, audio_path: str, language: str = "auto") -> TranscriptionResult:
        self.last_call = (audio_path, language)
        return TranscriptionResult(
            text="Cześć, to jest test.",
            language="pl" if language != "en" else "en",
            duration_s=3.2,
            processing_s=1.1,
        )


@pytest.fixture
def fake_transcriber(monkeypatch: pytest.MonkeyPatch) -> FakeTranscriber:
    fake = FakeTranscriber(ready=True)
    monkeypatch.setattr(main, "transcriber", fake)
    return fake


@pytest.fixture
def client() -> TestClient:
    # Constructed without a `with` block so the lifespan model-load never fires in tests.
    return TestClient(main.app, base_url="http://127.0.0.1")
