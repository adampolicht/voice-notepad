"""Tests for POST /api/transcribe (mocked model) plus an opt-in real integration test."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app import main
from tests.conftest import FakeTranscriber

FIXTURES = Path(__file__).parent / "fixtures"


def _audio(name: str = "clip.webm", data: bytes = b"fake-audio-bytes"):
    return {"audio": (name, data, "audio/webm")}


def test_transcribe_success(client, fake_transcriber) -> None:
    resp = client.post("/api/transcribe", files=_audio(), data={"language": "pl"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["text"] == "Cześć, to jest test."
    assert body["language"] == "pl"
    assert set(body) == {"text", "language", "duration_s", "processing_s"}
    assert fake_transcriber.last_call[1] == "pl"


def test_transcribe_defaults_language(client, fake_transcriber) -> None:
    resp = client.post("/api/transcribe", files=_audio())
    assert resp.status_code == 200
    # config default is "auto"
    assert fake_transcriber.last_call[1] == "auto"


def test_transcribe_missing_audio_returns_400(client, fake_transcriber) -> None:
    resp = client.post("/api/transcribe", data={"language": "pl"})
    assert resp.status_code in (400, 422)


def test_transcribe_empty_audio_returns_400(client, fake_transcriber) -> None:
    resp = client.post("/api/transcribe", files=_audio(data=b""))
    assert resp.status_code == 400


def test_transcribe_invalid_language_returns_400(client, fake_transcriber) -> None:
    resp = client.post("/api/transcribe", files=_audio(), data={"language": "de"})
    assert resp.status_code == 400


def test_transcribe_too_large_returns_413(client, fake_transcriber, monkeypatch) -> None:
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 4)
    resp = client.post("/api/transcribe", files=_audio(data=b"12345"))
    assert resp.status_code == 413


def test_transcribe_model_loading_returns_503(client, monkeypatch) -> None:
    monkeypatch.setattr(main, "transcriber", FakeTranscriber(ready=False))
    resp = client.post("/api/transcribe", files=_audio())
    assert resp.status_code == 503


@pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION") != "1",
    reason="set RUN_INTEGRATION=1 to run the real-model integration test (downloads a model)",
)
def test_transcribe_real_model_polish_diacritics(client) -> None:
    """End-to-end against the real model and the Polish fixture."""
    main.transcriber.load()
    with open(FIXTURES / "czesc_pl.wav", "rb") as fh:
        resp = client.post(
            "/api/transcribe",
            files={"audio": ("czesc_pl.wav", fh.read(), "audio/wav")},
            data={"language": "pl"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["language"] == "pl"
    # Diacritics must survive the round-trip.
    assert any(ch in body["text"] for ch in "ąćęłńóśźż")
