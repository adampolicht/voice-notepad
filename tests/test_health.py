"""Tests for GET /api/health."""

from __future__ import annotations

from tests.conftest import FakeTranscriber


def test_health_ok_when_ready(client, fake_transcriber) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"status": "ok", "model": "fake", "device": "cpu"}


def test_health_loading_when_not_ready(client, monkeypatch) -> None:
    from app import main

    monkeypatch.setattr(main, "transcriber", FakeTranscriber(ready=False))
    body = client.get("/api/health").json()
    assert body["status"] == "loading"


def test_foreign_host_header_rejected(client, fake_transcriber) -> None:
    resp = client.get("/api/notes", headers={"Host": "evil.example"})
    assert resp.status_code == 400
