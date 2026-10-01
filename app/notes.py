"""File-backed notes store: each note is a single JSON file on disk."""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

ID_RE = re.compile(r"^[0-9a-f]{32}$")
TITLE_FALLBACK = "Untitled note"
TITLE_MAX = 80


@dataclass
class Note:
    id: str
    title: str
    content: str
    created_at: float
    updated_at: float
    renamed: bool = False


def _derive_title(content: str) -> str:
    """Use the first non-empty line (trimmed) as the auto title for a note."""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:TITLE_MAX]
    return TITLE_FALLBACK


class NotesStore:
    """CRUD over notes persisted as individual JSON files in one directory."""

    def __init__(self, notes_dir: str | Path) -> None:
        self.dir = Path(notes_dir).expanduser()

    def _path(self, note_id: str) -> Path:
        """Resolve a note's file path, rejecting ids that could escape the dir."""
        if not ID_RE.match(note_id):
            raise ValueError(f"Invalid note id: {note_id!r}")
        return self.dir / f"{note_id}.json"

    def _read(self, path: Path) -> Note:
        return Note(**json.loads(path.read_text(encoding="utf-8")))

    def _write(self, note: Note) -> None:
        """Write atomically via a temp file so a crash can't leave a half-written note."""
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self._path(note.id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(asdict(note), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def list(self) -> list[Note]:
        """Return all notes, newest first; silently skip unreadable/corrupt files."""
        if not self.dir.exists():
            return []
        notes: list[Note] = []
        for path in self.dir.glob("*.json"):
            try:
                notes.append(self._read(path))
            except (json.JSONDecodeError, TypeError, OSError):
                continue
        notes.sort(key=lambda n: n.updated_at, reverse=True)
        return notes

    def get(self, note_id: str) -> Note | None:
        path = self._path(note_id)
        return self._read(path) if path.exists() else None

    def create(self, title: str = "", content: str = "") -> Note:
        now = time.time()
        title = title.strip()
        note = Note(
            id=uuid.uuid4().hex,
            title=title or _derive_title(content),
            content=content,
            created_at=now,
            updated_at=now,
            renamed=bool(title),
        )
        self._write(note)
        return note

    def update(
        self, note_id: str, *, content: str | None = None, title: str | None = None
    ) -> Note | None:
        """Update content and/or title. Title auto-tracks the first line until renamed."""
        note = self.get(note_id)
        if note is None:
            return None
        if title is not None:
            note.title = title.strip() or TITLE_FALLBACK
            note.renamed = True
        if content is not None:
            note.content = content
            if not note.renamed:
                note.title = _derive_title(content)
        note.updated_at = time.time()
        self._write(note)
        return note

    def delete(self, note_id: str) -> bool:
        path = self._path(note_id)
        if not path.exists():
            return False
        path.unlink()
        return True
