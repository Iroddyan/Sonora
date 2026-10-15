from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from sonora.models import Track, from_row


SUPPORTED_SCHEMA_VERSION = 2
TRACK_COLUMNS = "id, path, title, artist, album_artist, album, genre, track_number, disc_number, year, duration_ms, artwork_path, artwork_accent"


def default_database_path() -> Path:
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    # Keep the old Qt application's established location so an index survives the UI migration.
    return data_home / "Sonora" / "Sonora" / "library.sqlite"


class LibraryDatabase:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def _initialize(self) -> None:
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""CREATE TABLE IF NOT EXISTS library_folders (
                path TEXT PRIMARY KEY NOT NULL,
                added_at TEXT NOT NULL,
                last_scanned_at TEXT
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL UNIQUE,
                source_root TEXT NOT NULL,
                title TEXT NOT NULL,
                artist TEXT NOT NULL DEFAULT '',
                album_artist TEXT NOT NULL DEFAULT '',
                album TEXT NOT NULL DEFAULT '',
                genre TEXT NOT NULL DEFAULT '',
                composer TEXT NOT NULL DEFAULT '',
                track_number INTEGER NOT NULL DEFAULT 0,
                disc_number INTEGER NOT NULL DEFAULT 0,
                year INTEGER NOT NULL DEFAULT 0,
                duration_ms INTEGER NOT NULL DEFAULT 0,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                modified_ms INTEGER NOT NULL DEFAULT 0,
                last_scanned_at TEXT NOT NULL,
                artwork_path TEXT NOT NULL DEFAULT '',
                artwork_accent TEXT NOT NULL DEFAULT ''
            )""")
            columns = {row[1] for row in conn.execute("PRAGMA table_info(tracks)")}
            if "artwork_path" not in columns:
                conn.execute("ALTER TABLE tracks ADD COLUMN artwork_path TEXT NOT NULL DEFAULT ''")
            if "artwork_accent" not in columns:
                conn.execute("ALTER TABLE tracks ADD COLUMN artwork_accent TEXT NOT NULL DEFAULT ''")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tracks_album_artist ON tracks(album_artist, album)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tracks_source_root ON tracks(source_root)")
            conn.execute(f"PRAGMA user_version={SUPPORTED_SCHEMA_VERSION}")

    def folders(self) -> list[str]:
        with self.connect() as conn:
            return [row[0] for row in conn.execute("SELECT path FROM library_folders ORDER BY path COLLATE NOCASE")]

    def add_folder(self, path: str) -> bool:
        path = str(Path(path).expanduser().resolve())
        current = [Path(folder) for folder in self.folders()]
        candidate = Path(path)
        if any(candidate == existing or candidate.is_relative_to(existing) or existing.is_relative_to(candidate)
               for existing in current):
            return False
        with self.connect() as conn:
            conn.execute("INSERT OR IGNORE INTO library_folders(path, added_at) VALUES (?, datetime('now'))", (path,))
        return True

    def remove_folder(self, path: str) -> None:
        normalized = str(Path(path).expanduser().resolve())
        with self.connect() as conn:
            conn.execute("DELETE FROM tracks WHERE source_root=?", (normalized,))
            conn.execute("DELETE FROM library_folders WHERE path=?", (normalized,))

    def tracks(self) -> list[Track]:
        with self.connect() as conn:
            rows = conn.execute(f"SELECT {TRACK_COLUMNS} FROM tracks ORDER BY title COLLATE NOCASE, artist COLLATE NOCASE")
            return [from_row(row) for row in rows]

    def search(self, text: str) -> list[Track]:
        tracks = self.tracks()
        query = " ".join(text.casefold().split())
        if not query:
            return tracks
        tokens = query.split()

        def searchable(track: Track) -> str:
            return " ".join((track.title, track.artist, track.album_artist, track.album, track.genre)).casefold()

        direct = [track for track in tracks if all(token in searchable(track) for token in tokens)]
        if direct:
            return direct

        def score(track: Track) -> tuple[int, str, str]:
            best = max((_similarity(query, item.casefold()) for item in (track.title, track.artist, track.album)), default=0)
            if best >= 0.52:
                return (int((1 - best) * 1000), track.title.casefold(), track.artist.casefold())
            return (10_000, track.title.casefold(), track.artist.casefold())

        return [track for track in sorted(tracks, key=score) if score(track)[0] < 10_000]


def _similarity(query: str, candidate: str) -> float:
    from difflib import SequenceMatcher

    if not candidate or not query:
        return 0.0
    return max(SequenceMatcher(None, query, candidate).ratio(),
               max((SequenceMatcher(None, query, word).ratio() for word in candidate.split()), default=0.0))
