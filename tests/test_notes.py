"""Tests for the notes store and the /api/notes CRUD endpoints (temp dir, no model)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import main
from app.notes import NotesStore


@pytest.fixture
def store(tmp_path, monkeypatch) -> NotesStore:
    """Point the app's notes store at a throwaway directory."""
    s = NotesStore(tmp_path / "notes")
    monkeypatch.setattr(main, "notes", s)
    return s


@pytest.fixture
def notes_client(store) -> TestClient:
    return TestClient(main.app, base_url="http://127.0.0.1")


# ---- store unit tests ----


def test_create_derives_title_from_first_line(store) -> None:
    note = store.create(content="  First line\nsecond line")
    assert note.title == "First line"
    assert not note.renamed
    assert store.get(note.id).content == "  First line\nsecond line"


def test_create_empty_uses_fallback_title(store) -> None:
    note = store.create(content="   \n  ")
    assert note.title == "Untitled note"


def test_update_content_retracks_title_until_renamed(store) -> None:
    note = store.create(content="old")
    store.update(note.id, title="My name")
    updated = store.update(note.id, content="new first line")
    assert updated.title == "My name"  # manual title sticks
    assert updated.renamed is True


def test_list_sorted_newest_first(store) -> None:
    a = store.create(content="a")
    b = store.create(content="b")
    ids = [n.id for n in store.list()]
    assert ids[0] == b.id and a.id in ids


def test_delete_removes_file(store) -> None:
    note = store.create(content="x")
    assert store.delete(note.id) is True
    assert store.get(note.id) is None
    assert store.delete(note.id) is False


def test_invalid_id_rejected(store) -> None:
    with pytest.raises(ValueError):
        store.get("../etc/passwd")


def test_list_skips_corrupt_files(store) -> None:
    store.create(content="good")
    (store.dir / "garbage.json").write_text("{not json", encoding="utf-8")
    assert len(store.list()) == 1


# ---- API tests ----


def test_api_crud_roundtrip(notes_client) -> None:
    created = notes_client.post("/api/notes", json={"content": "Hello note"})
    assert created.status_code == 201
    note_id = created.json()["id"]

    listed = notes_client.get("/api/notes").json()
    assert any(n["id"] == note_id for n in listed)
    assert "content" not in listed[0]  # summaries omit the body

    full = notes_client.get(f"/api/notes/{note_id}").json()
    assert full["content"] == "Hello note"
    assert full["title"] == "Hello note"

    updated = notes_client.put(f"/api/notes/{note_id}", json={"content": "Changed"})
    assert updated.json()["content"] == "Changed"

    renamed = notes_client.put(f"/api/notes/{note_id}", json={"title": "Custom"})
    assert renamed.json()["title"] == "Custom"
    assert renamed.json()["renamed"] is True

    assert notes_client.delete(f"/api/notes/{note_id}").status_code == 204
    assert notes_client.get(f"/api/notes/{note_id}").status_code == 404


def test_api_get_missing_returns_404(notes_client) -> None:
    resp = notes_client.get("/api/notes/" + "0" * 32)
    assert resp.status_code == 404


def test_api_invalid_id_returns_400(notes_client) -> None:
    assert notes_client.get("/api/notes/not-a-valid-id").status_code == 400
    assert notes_client.delete("/api/notes/not-a-valid-id").status_code == 400
