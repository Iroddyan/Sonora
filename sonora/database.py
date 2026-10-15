from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from sonora.models import Track, from_row


SUPPORTED_SCHEMA_VERSION = 3
QUALIFYING_LISTEN_MS = 30_000
TRACK_COLUMNS = "id, path, title, artist, album_artist, album, genre, track_number, disc_number, year, duration_ms, artwork_path, artwork_accent, first_added_at"


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
                artwork_accent TEXT NOT NULL DEFAULT '',
                first_added_at TEXT NOT NULL DEFAULT ''
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS playback_history (
                id INTEGER PRIMARY KEY,
                track_path TEXT NOT NULL,
                title TEXT NOT NULL,
                artist TEXT NOT NULL DEFAULT '',
                album_artist TEXT NOT NULL DEFAULT '',
                album TEXT NOT NULL DEFAULT '',
                duration_ms INTEGER NOT NULL DEFAULT 0,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                listened_ms INTEGER NOT NULL DEFAULT 0,
                qualified INTEGER NOT NULL DEFAULT 0,
                end_reason TEXT NOT NULL DEFAULT ''
            )""")
            columns = {row[1] for row in conn.execute("PRAGMA table_info(tracks)")}
            if "artwork_path" not in columns:
                conn.execute("ALTER TABLE tracks ADD COLUMN artwork_path TEXT NOT NULL DEFAULT ''")
            if "artwork_accent" not in columns:
                conn.execute("ALTER TABLE tracks ADD COLUMN artwork_accent TEXT NOT NULL DEFAULT ''")
            if "first_added_at" not in columns:
                conn.execute("ALTER TABLE tracks ADD COLUMN first_added_at TEXT NOT NULL DEFAULT ''")
            # Older indexes only remembered the last scan. Use that as a one-time
            # baseline; later rescans preserve first_added_at unchanged.
            conn.execute("""UPDATE tracks SET first_added_at=COALESCE(NULLIF(last_scanned_at, ''), datetime('now'))
                WHERE first_added_at=''""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tracks_album_artist ON tracks(album_artist, album)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tracks_source_root ON tracks(source_root)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_playback_history_started ON playback_history(started_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_playback_history_path ON playback_history(track_path, started_at DESC)")
            conn.execute("""UPDATE playback_history SET ended_at=datetime('now'), end_reason='interrupted',
                qualified=CASE WHEN listened_ms >= CASE WHEN duration_ms > 0 THEN MIN(?, duration_ms / 2) ELSE ? END THEN 1 ELSE 0 END
                WHERE ended_at IS NULL""", (QUALIFYING_LISTEN_MS, QUALIFYING_LISTEN_MS))
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

    def start_playback(self, track: Track, started_at: str | None = None) -> int:
        with self.connect() as conn:
            cursor = conn.execute("""INSERT INTO playback_history(
                track_path, title, artist, album_artist, album, duration_ms, started_at
            ) VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')))""",
                (track.path, track.title, track.artist, track.album_artist, track.album,
                 track.duration_ms, started_at))
            return int(cursor.lastrowid)

    def add_listened_time(self, session_id: int, listened_ms: int) -> None:
        listened_ms = max(0, int(listened_ms))
        if not listened_ms:
            return
        with self.connect() as conn:
            conn.execute("UPDATE playback_history SET listened_ms=listened_ms+? WHERE id=? AND ended_at IS NULL",
                         (listened_ms, session_id))

    def finish_playback(self, session_id: int, end_reason: str, final_listened_ms: int = 0) -> None:
        final_listened_ms = max(0, int(final_listened_ms))
        with self.connect() as conn:
            conn.execute("""UPDATE playback_history SET
                listened_ms=listened_ms+?, ended_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), end_reason=?,
                qualified=CASE WHEN listened_ms+? >=
                    CASE WHEN duration_ms > 0 THEN MIN(?, duration_ms / 2) ELSE ? END
                    THEN 1 ELSE 0 END
                WHERE id=? AND ended_at IS NULL""",
                (final_listened_ms, end_reason, final_listened_ms, QUALIFYING_LISTEN_MS,
                 QUALIFYING_LISTEN_MS, session_id))

    def playback_history(self, limit: int = 100, qualified_only: bool = False) -> list[dict]:
        limit = max(1, min(int(limit), 1000))
        clause = "WHERE qualified=1" if qualified_only else ""
        with self.connect() as conn:
            rows = conn.execute(f"""SELECT id, track_path, title, artist, album_artist, album,
                duration_ms, started_at, ended_at, listened_ms, qualified, end_reason
                FROM playback_history {clause} ORDER BY started_at DESC, id DESC LIMIT ?""", (limit,))
            return [dict(row) for row in rows]

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
