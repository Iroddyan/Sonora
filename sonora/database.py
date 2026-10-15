from __future__ import annotations

import os
import sqlite3
import unicodedata
from pathlib import Path

from sonora.credits import DEFAULT_ARTIST_EXCEPTIONS, normalize_name, split_artist_credits
from sonora.models import Track, from_row


SUPPORTED_SCHEMA_VERSION = 5
QUALIFYING_LISTEN_MS = 240_000
TRACK_COLUMNS = """t.id, t.path, t.title, t.album_artist, t.album, t.genre, t.composer, t.track_number,
    t.disc_number, t.year, t.duration_ms, t.artwork_path, t.artwork_accent, t.first_seen_at,
    t.size_bytes, t.modified_ms, t.missing, t.play_count, t.last_played_at,
    COALESCE((SELECT name FROM artists WHERE id=(SELECT artist_id FROM track_credits
        WHERE track_id=t.id AND role='primary' ORDER BY ordinal LIMIT 1)), t.artist, '') AS primary_artist,
    COALESCE((SELECT group_concat(name, ', ') FROM (SELECT ar.name AS name FROM track_credits tc
        JOIN artists ar ON ar.id=tc.artist_id WHERE tc.track_id=t.id AND tc.role IN ('primary','featured')
    ORDER BY CASE tc.role WHEN 'primary' THEN 0 ELSE 1 END, tc.ordinal)), t.artist, '') AS display_artist"""


class _ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, traceback):
        try:
            return super().__exit__(exc_type, exc, traceback)
        finally:
            self.close()


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
        conn = sqlite3.connect(self.path, timeout=10, factory=_ClosingConnection)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def setting(self, key: str, default=None):
        """Read a small application preference from the shared settings table."""
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM library_settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as conn:
            conn.execute("INSERT INTO library_settings(key, value) VALUES (?, ?) "
                         "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))

    def _initialize(self) -> None:
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            previous_version = conn.execute("PRAGMA user_version").fetchone()[0]
            conn.execute("""CREATE TABLE IF NOT EXISTS artists (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                normalized_name TEXT NOT NULL UNIQUE
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS albums (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                normalized_title TEXT NOT NULL,
                album_artist_id INTEGER REFERENCES artists(id),
                tie_break_folder TEXT NOT NULL DEFAULT '',
                artwork_path TEXT NOT NULL DEFAULT '',
                UNIQUE(normalized_title, album_artist_id)
            )""")
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
                first_added_at TEXT NOT NULL DEFAULT '',
                first_seen_at TEXT NOT NULL DEFAULT '',
                play_count INTEGER NOT NULL DEFAULT 0,
                last_played_at TEXT NOT NULL DEFAULT '',
                missing INTEGER NOT NULL DEFAULT 0,
                album_id INTEGER REFERENCES albums(id)
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS track_credits (
                track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
                artist_id INTEGER NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK(role IN ('primary', 'featured', 'album')),
                ordinal INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(track_id, artist_id, role)
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
            conn.execute("""CREATE TABLE IF NOT EXISTS favorites (
                track_id INTEGER PRIMARY KEY REFERENCES tracks(id) ON DELETE CASCADE,
                added_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS playlist_tracks (
                playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
                track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
                position INTEGER NOT NULL,
                added_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                PRIMARY KEY(playlist_id, track_id),
                UNIQUE(playlist_id, position)
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS metadata_overrides (
                track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
                field TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                PRIMARY KEY(track_id, field)
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS artist_split_exceptions (
                normalized_name TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS library_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS duplicate_candidates (
                track_a_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
                track_b_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
                duration_delta_ms INTEGER NOT NULL,
                detected_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                PRIMARY KEY(track_a_id, track_b_id),
                CHECK(track_a_id < track_b_id)
            )""")
            columns = {row[1] for row in conn.execute("PRAGMA table_info(tracks)")}
            additions = {
                "artwork_path": "TEXT NOT NULL DEFAULT ''",
                "artwork_accent": "TEXT NOT NULL DEFAULT ''",
                "first_added_at": "TEXT NOT NULL DEFAULT ''",
                "first_seen_at": "TEXT NOT NULL DEFAULT ''",
                "play_count": "INTEGER NOT NULL DEFAULT 0",
                "last_played_at": "TEXT NOT NULL DEFAULT ''",
                "missing": "INTEGER NOT NULL DEFAULT 0",
                "album_id": "INTEGER REFERENCES albums(id)",
            }
            for name, definition in additions.items():
                if name not in columns:
                    conn.execute(f"ALTER TABLE tracks ADD COLUMN {name} {definition}")
            # Seed the canonical first-seen timestamp from file mtime when possible.
            conn.execute("""UPDATE tracks SET first_seen_at=COALESCE(
                NULLIF(first_seen_at, ''),
                CASE WHEN modified_ms > 0 THEN strftime('%Y-%m-%dT%H:%M:%fZ', modified_ms / 1000.0, 'unixepoch') END,
                NULLIF(first_added_at, ''), NULLIF(last_scanned_at, ''), datetime('now'))""")
            conn.execute("UPDATE tracks SET first_added_at=first_seen_at WHERE first_added_at='' OR first_added_at!=first_seen_at")
            exceptions_initialized = conn.execute(
                "SELECT 1 FROM library_settings WHERE key='artist_split_exceptions_initialized'").fetchone()
            if not exceptions_initialized:
                for name in DEFAULT_ARTIST_EXCEPTIONS:
                    conn.execute("INSERT INTO artist_split_exceptions(normalized_name, name) VALUES (?, ?)",
                                 (normalize_name(name), name))
                conn.execute("INSERT INTO library_settings(key, value) VALUES ('artist_split_exceptions_initialized', '1')")
            if previous_version < SUPPORTED_SCHEMA_VERSION:
                self._rebuild_entities(conn)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tracks_album_artist ON tracks(album_artist, album)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tracks_source_root ON tracks(source_root)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tracks_missing ON tracks(missing)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tracks_duplicate_keys ON tracks(title, artist, duration_ms)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_track_credits_artist ON track_credits(artist_id, role, track_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_playback_history_started ON playback_history(started_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_playback_history_path ON playback_history(track_path, started_at DESC)")
            if previous_version < 5:
                conn.execute("""UPDATE playback_history SET qualified=CASE WHEN listened_ms >=
                    CASE WHEN duration_ms > 0 THEN MIN(?, duration_ms / 2) ELSE ? END
                    THEN 1 ELSE 0 END WHERE ended_at IS NOT NULL""",
                    (QUALIFYING_LISTEN_MS, QUALIFYING_LISTEN_MS))
            unfinished = {row["id"]: bool(row["qualified"]) for row in conn.execute(
                "SELECT id, qualified FROM playback_history WHERE ended_at IS NULL")}
            conn.execute("""UPDATE playback_history SET ended_at=datetime('now'), end_reason='interrupted',
                qualified=CASE WHEN listened_ms >= CASE WHEN duration_ms > 0 THEN MIN(?, duration_ms / 2) ELSE ? END THEN 1 ELSE 0 END
                WHERE ended_at IS NULL""", (QUALIFYING_LISTEN_MS, QUALIFYING_LISTEN_MS))
            if previous_version < 5:
                conn.execute("""UPDATE tracks SET play_count=COALESCE((SELECT COUNT(*) FROM playback_history h
                    WHERE h.track_path=tracks.path AND h.qualified=1), 0),
                    last_played_at=COALESCE((SELECT MAX(started_at) FROM playback_history h
                    WHERE h.track_path=tracks.path AND h.qualified=1), '')""")
            else:
                for session_id, previously_qualified in unfinished.items():
                    current = conn.execute("SELECT qualified FROM playback_history WHERE id=?", (session_id,)).fetchone()
                    if current and current[0] and not previously_qualified:
                        self._count_qualified_play(conn, session_id)
            conn.execute(f"PRAGMA user_version={SUPPORTED_SCHEMA_VERSION}")

    @staticmethod
    def _artist_id(conn: sqlite3.Connection, name: str) -> int:
        normalized = normalize_name(name)
        conn.execute("INSERT OR IGNORE INTO artists(name, normalized_name) VALUES (?, ?)", (name.strip(), normalized))
        return int(conn.execute("SELECT id FROM artists WHERE normalized_name=?", (normalized,)).fetchone()[0])

    @classmethod
    def _rebuild_entities(cls, conn: sqlite3.Connection) -> None:
        """Reconcile normalized people and album identities from indexed track tags."""
        exceptions = [row[0] for row in conn.execute("SELECT name FROM artist_split_exceptions")]
        conn.execute("DELETE FROM track_credits")
        conn.execute("UPDATE tracks SET album_id=NULL")
        conn.execute("DELETE FROM albums")
        conn.execute("DELETE FROM artists")
        rows = conn.execute("""SELECT id, artist, album_artist, album, source_root, artwork_path
            FROM tracks ORDER BY lower(source_root), id""").fetchall()
        for row in rows:
            primary, featured = split_artist_credits([row["artist"]], exceptions)
            credits = [(name, role) for name, role in
                       ([(primary, "primary")] + [(name, "featured") for name in featured]) if name]
            for ordinal, (name, role) in enumerate(credits):
                artist_id = cls._artist_id(conn, name)
                conn.execute("INSERT OR IGNORE INTO track_credits(track_id, artist_id, role, ordinal) VALUES (?, ?, ?, ?)",
                             (row["id"], artist_id, role, ordinal))
            album_artist = row["album_artist"].strip() or primary
            grouping_artist = album_artist or "Unknown artist"
            album_id = None
            if album_artist:
                artist_id = cls._artist_id(conn, album_artist)
                conn.execute("INSERT OR IGNORE INTO track_credits(track_id, artist_id, role, ordinal) VALUES (?, ?, 'album', 0)",
                             (row["id"], artist_id))
            album = row["album"].strip()
            if album:
                normalized_title = normalize_name(album)
                album_artist_id = cls._artist_id(conn, grouping_artist)
                conn.execute("""INSERT OR IGNORE INTO albums(title, normalized_title, album_artist_id,
                    tie_break_folder, artwork_path) VALUES (?, ?, ?, ?, ?)""",
                    (album, normalized_title, album_artist_id, row["source_root"], row["artwork_path"]))
                result = conn.execute("SELECT id FROM albums WHERE normalized_title=? AND album_artist_id IS ?",
                                      (normalized_title, album_artist_id)).fetchone()
                album_id = int(result[0])
                conn.execute("""UPDATE albums SET tie_break_folder=MIN(tie_break_folder, ?),
                    artwork_path=CASE WHEN artwork_path='' THEN ? ELSE artwork_path END WHERE id=?""",
                    (row["source_root"], row["artwork_path"], album_id))
            conn.execute("UPDATE tracks SET album_id=? WHERE id=?", (album_id, row["id"]))
        cls._rebuild_duplicate_candidates(conn)

    @staticmethod
    def _rebuild_duplicate_candidates(conn: sqlite3.Connection) -> None:
        conn.execute("DELETE FROM duplicate_candidates")
        tracks = conn.execute("""SELECT t.id, t.title, t.duration_ms,
            COALESCE((SELECT normalized_name FROM artists ar JOIN track_credits tc ON tc.artist_id=ar.id
                WHERE tc.track_id=t.id AND tc.role='primary' ORDER BY tc.ordinal LIMIT 1), '') AS primary_artist
            FROM tracks t WHERE t.missing=0 AND t.duration_ms>0 ORDER BY t.id""").fetchall()
        groups: dict[tuple[str, str], list[sqlite3.Row]] = {}
        for track in tracks:
            title_key = normalize_name(track["title"])
            artist_key = track["primary_artist"]
            if title_key and artist_key:
                groups.setdefault((title_key, artist_key), []).append(track)
        for group in groups.values():
            group.sort(key=lambda track: (track["duration_ms"], track["id"]))
            for index, first in enumerate(group):
                for second in group[index + 1:]:
                    delta = int(second["duration_ms"]) - int(first["duration_ms"])
                    if delta > 2_000:
                        break
                    conn.execute("""INSERT INTO duplicate_candidates(track_a_id, track_b_id, duration_delta_ms)
                        VALUES (?, ?, ?)""", (min(first["id"], second["id"]), max(first["id"], second["id"]), delta))

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
            conn.execute("UPDATE tracks SET missing=1 WHERE source_root=?", (normalized,))
            self._rebuild_duplicate_candidates(conn)
            conn.execute("DELETE FROM library_folders WHERE path=?", (normalized,))

    def tracks(self, include_missing: bool = False) -> list[Track]:
        with self.connect() as conn:
            where = "" if include_missing else "WHERE t.missing=0"
            rows = conn.execute(f"SELECT {TRACK_COLUMNS} FROM tracks t {where} ORDER BY t.title COLLATE NOCASE, t.artist COLLATE NOCASE")
            return [from_row(row) for row in rows]

    def album_groups(self) -> list[tuple[str, str, list[Track], str]]:
        with self.connect() as conn:
            groups = conn.execute("""SELECT al.id, al.title, ar.name AS artist, al.tie_break_folder
                FROM albums al LEFT JOIN artists ar ON ar.id=al.album_artist_id
                WHERE EXISTS (SELECT 1 FROM tracks t WHERE t.album_id=al.id AND t.missing=0)
                ORDER BY al.normalized_title, COALESCE(ar.normalized_name, ''), al.tie_break_folder""").fetchall()
            result = []
            for group in groups:
                rows = conn.execute(f"""SELECT {TRACK_COLUMNS} FROM tracks t WHERE t.album_id=? AND t.missing=0
                    ORDER BY t.disc_number, t.track_number, t.title COLLATE NOCASE""", (group["id"],)).fetchall()
                result.append((group["title"], group["artist"] or "Unknown artist",
                               [from_row(row) for row in rows], group["tie_break_folder"]))
            return result

    def artist_groups(self) -> list[tuple[str, list[Track]]]:
        with self.connect() as conn:
            artists = conn.execute("""SELECT DISTINCT ar.id, ar.name FROM artists ar
                JOIN track_credits tc ON tc.artist_id=ar.id WHERE tc.role IN ('primary','featured','album')
                AND EXISTS (SELECT 1 FROM tracks available WHERE available.id=tc.track_id AND available.missing=0)
                ORDER BY ar.normalized_name""").fetchall()
            result = []
            for artist in artists:
                rows = conn.execute(f"""SELECT DISTINCT {TRACK_COLUMNS} FROM tracks t
                    JOIN track_credits tc ON tc.track_id=t.id WHERE tc.artist_id=?
                    AND tc.role IN ('primary','featured','album') AND t.missing=0 ORDER BY t.title COLLATE NOCASE""",
                    (artist["id"],)).fetchall()
                result.append((artist["name"], [from_row(row) for row in rows]))
            return result

    def artist_split_exceptions(self) -> list[str]:
        with self.connect() as conn:
            return [row[0] for row in conn.execute(
                "SELECT name FROM artist_split_exceptions ORDER BY normalized_name")]

    def set_artist_split_exceptions(self, names) -> None:
        cleaned = []
        for name in names:
            value = " ".join(str(name).split())
            key = normalize_name(value)
            if value and key and all(key != normalize_name(existing) for existing in cleaned):
                cleaned.append(value)
        with self.connect() as conn:
            conn.execute("DELETE FROM artist_split_exceptions")
            conn.executemany("INSERT INTO artist_split_exceptions(normalized_name, name) VALUES (?, ?)",
                             ((normalize_name(name), name) for name in cleaned))
            self._rebuild_entities(conn)

    def set_override(self, track_id: int, field: str, value: str) -> None:
        allowed = {"title", "artist", "album_artist", "album", "genre", "composer", "year",
                   "track_number", "disc_number"}
        if field not in allowed:
            raise ValueError(f"Unsupported metadata field: {field}")
        with self.connect() as conn:
            conn.execute("""INSERT INTO metadata_overrides(track_id, field, value) VALUES (?, ?, ?)
                ON CONFLICT(track_id, field) DO UPDATE SET value=excluded.value,
                    updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now')""", (track_id, field, str(value)))
            column = field
            column_value = str(value)
            if field in {"year", "track_number", "disc_number"}:
                try:
                    column_value = str(max(0, int(value)))
                except (TypeError, ValueError):
                    column_value = "0"
            conn.execute(f"UPDATE tracks SET {column}=? WHERE id=?", (column_value, track_id))
            if field in {"title", "artist", "album_artist", "album"}:
                self._rebuild_entities(conn)

    def clear_override(self, track_id: int, field: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM metadata_overrides WHERE track_id=? AND field=?", (track_id, field))
            conn.execute("UPDATE tracks SET size_bytes=-1 WHERE id=?", (track_id,))

    def overrides(self, track_id: int) -> dict[str, str]:
        with self.connect() as conn:
            return {row["field"]: row["value"] for row in conn.execute(
                "SELECT field, value FROM metadata_overrides WHERE track_id=?", (track_id,))}

    def favorite_track(self, track_id: int, favorite: bool = True) -> None:
        with self.connect() as conn:
            if favorite:
                conn.execute("INSERT OR IGNORE INTO favorites(track_id) VALUES (?)", (track_id,))
            else:
                conn.execute("DELETE FROM favorites WHERE track_id=?", (track_id,))

    def is_favorite(self, track_id: int) -> bool:
        if not track_id:
            return False
        with self.connect() as conn:
            return conn.execute("SELECT 1 FROM favorites WHERE track_id=?", (track_id,)).fetchone() is not None

    def favorite_paths(self) -> set[str]:
        with self.connect() as conn:
            return {row[0] for row in conn.execute("""SELECT t.path FROM favorites f
                JOIN tracks t ON t.id=f.track_id WHERE t.missing=0""")}

    def favorites(self) -> list[Track]:
        with self.connect() as conn:
            rows = conn.execute(f"""SELECT {TRACK_COLUMNS} FROM tracks t
                JOIN favorites f ON f.track_id=t.id WHERE t.missing=0
                ORDER BY f.added_at DESC, lower(t.title)""").fetchall()
            return [from_row(row) for row in rows]

    def create_playlist(self, name: str) -> int:
        name = " ".join(name.split())
        if not name:
            raise ValueError("Playlist name cannot be empty")
        with self.connect() as conn:
            cursor = conn.execute("INSERT INTO playlists(name) VALUES (?)", (name,))
            return int(cursor.lastrowid)

    def playlists(self) -> list[dict]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("""SELECT p.id, p.name, p.created_at, p.updated_at,
                COUNT(pt.track_id) AS track_count FROM playlists p LEFT JOIN playlist_tracks pt
                ON pt.playlist_id=p.id GROUP BY p.id ORDER BY lower(p.name)""")]

    def rename_playlist(self, playlist_id: int, name: str) -> None:
        name = " ".join(name.split())
        if not name:
            raise ValueError("Playlist name cannot be empty")
        with self.connect() as conn:
            conn.execute("UPDATE playlists SET name=?, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id=?",
                         (name, playlist_id))

    def delete_playlist(self, playlist_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM playlists WHERE id=?", (playlist_id,))

    def playlist_tracks(self, playlist_id: int) -> list[Track]:
        with self.connect() as conn:
            rows = conn.execute(f"""SELECT {TRACK_COLUMNS} FROM playlist_tracks pt
                JOIN tracks t ON t.id=pt.track_id WHERE pt.playlist_id=? AND t.missing=0
                ORDER BY pt.position""", (playlist_id,)).fetchall()
            return [from_row(row) for row in rows]

    def add_playlist_track(self, playlist_id: int, track_id: int, position: int | None = None) -> None:
        with self.connect() as conn:
            if position is None:
                position = int(conn.execute(
                    "SELECT COALESCE(MAX(position)+1, 0) FROM playlist_tracks WHERE playlist_id=?",
                    (playlist_id,)).fetchone()[0])
            conn.execute("INSERT OR IGNORE INTO playlist_tracks(playlist_id, track_id, position) VALUES (?, ?, ?)",
                         (playlist_id, track_id, position))
            conn.execute("UPDATE playlists SET updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id=?",
                         (playlist_id,))

    def remove_playlist_track(self, playlist_id: int, track_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=? AND track_id=?", (playlist_id, track_id))
            self._renumber_playlist(conn, playlist_id)

    @staticmethod
    def _renumber_playlist(conn: sqlite3.Connection, playlist_id: int) -> None:
        rows = conn.execute("SELECT track_id FROM playlist_tracks WHERE playlist_id=? ORDER BY position",
                            (playlist_id,)).fetchall()
        conn.execute("UPDATE playlist_tracks SET position=-position-1 WHERE playlist_id=?", (playlist_id,))
        conn.executemany("UPDATE playlist_tracks SET position=? WHERE playlist_id=? AND track_id=?",
                         ((position, playlist_id, row[0]) for position, row in enumerate(rows)))
        conn.execute("UPDATE playlists SET updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id=?",
                     (playlist_id,))

    def move_playlist_track(self, playlist_id: int, track_id: int, target_track_id: int) -> bool:
        with self.connect() as conn:
            rows = [row[0] for row in conn.execute(
                "SELECT track_id FROM playlist_tracks WHERE playlist_id=? ORDER BY position", (playlist_id,))]
            if track_id not in rows or target_track_id not in rows:
                return False
            rows.remove(track_id)
            rows.insert(rows.index(target_track_id), track_id)
            conn.execute("UPDATE playlist_tracks SET position=-position-1 WHERE playlist_id=?", (playlist_id,))
            conn.executemany("UPDATE playlist_tracks SET position=? WHERE playlist_id=? AND track_id=?",
                             ((position, playlist_id, value) for position, value in enumerate(rows)))
            conn.execute("UPDATE playlists SET updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id=?",
                         (playlist_id,))
            return True

    def recently_played_paths(self, limit: int = 20) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute("""SELECT track_path, MAX(started_at) AS latest, MAX(id) AS latest_id
                FROM playback_history WHERE listened_ms>0 GROUP BY track_path
                ORDER BY latest DESC, latest_id DESC LIMIT ?""", (max(1, min(int(limit), 100)),))
            return [row[0] for row in rows]

    def rediscover_tracks(self, limit: int = 20) -> list[Track]:
        with self.connect() as conn:
            rows = conn.execute(f"""SELECT {TRACK_COLUMNS} FROM tracks t WHERE t.missing=0
                AND date(t.first_seen_at) <= date('now', '-90 days')
                AND (t.last_played_at='' OR date(t.last_played_at) <= date('now', '-90 days'))
                ORDER BY COALESCE(NULLIF(t.last_played_at,''), t.first_seen_at), lower(t.title) LIMIT ?""",
                (max(1, min(int(limit), 100)),)).fetchall()
            return [from_row(row) for row in rows]

    def duplicate_candidates(self) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("""SELECT a.path AS path_a, a.title AS title_a, b.path AS path_b,
                b.title AS title_b, d.duration_delta_ms FROM duplicate_candidates d
                JOIN tracks a ON a.id=d.track_a_id JOIN tracks b ON b.id=d.track_b_id
                ORDER BY a.title COLLATE NOCASE, a.path""").fetchall()
            return [dict(row) for row in rows]

    def start_playback(self, track: Track, started_at: str | None = None) -> int:
        with self.connect() as conn:
            timestamp = started_at or None
            cursor = conn.execute("""INSERT INTO playback_history(
                track_path, title, artist, album_artist, album, duration_ms, started_at
            ) VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')))""",
                (track.path, track.title, track.artist, track.album_artist, track.album,
                 track.duration_ms, timestamp))
            return int(cursor.lastrowid)

    def add_listened_time(self, session_id: int, listened_ms: int) -> bool:
        listened_ms = max(0, int(listened_ms))
        if not listened_ms:
            return False
        with self.connect() as conn:
            session = conn.execute("SELECT track_path, duration_ms, listened_ms, qualified FROM playback_history "
                                   "WHERE id=? AND ended_at IS NULL", (session_id,)).fetchone()
            if not session:
                return False
            total = session["listened_ms"] + listened_ms
            threshold = (min(QUALIFYING_LISTEN_MS, session["duration_ms"] // 2)
                         if session["duration_ms"] > 0 else QUALIFYING_LISTEN_MS)
            qualified = total >= threshold
            conn.execute("UPDATE playback_history SET listened_ms=?, qualified=? WHERE id=? AND ended_at IS NULL",
                         (total, int(qualified), session_id))
            if qualified and not session["qualified"]:
                self._count_qualified_play(conn, session_id)
                return True
            return False

    def finish_playback(self, session_id: int, end_reason: str, final_listened_ms: int = 0) -> bool:
        final_listened_ms = max(0, int(final_listened_ms))
        with self.connect() as conn:
            before = conn.execute("SELECT qualified FROM playback_history WHERE id=? AND ended_at IS NULL",
                                  (session_id,)).fetchone()
            cursor = conn.execute("""UPDATE playback_history SET
                listened_ms=listened_ms+?, ended_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), end_reason=?,
                qualified=CASE WHEN listened_ms+? >=
                    CASE WHEN duration_ms > 0 THEN MIN(?, duration_ms / 2) ELSE ? END
                    THEN 1 ELSE 0 END
                WHERE id=? AND ended_at IS NULL""",
                (final_listened_ms, end_reason, final_listened_ms, QUALIFYING_LISTEN_MS,
                 QUALIFYING_LISTEN_MS, session_id))
            if cursor.rowcount and before and not before[0]:
                qualified = conn.execute("SELECT qualified FROM playback_history WHERE id=?", (session_id,)).fetchone()
                if qualified and qualified[0]:
                    self._count_qualified_play(conn, session_id)
                    return True
            return False

    @staticmethod
    def _count_qualified_play(conn: sqlite3.Connection, session_id: int) -> None:
        conn.execute("""UPDATE tracks SET play_count=play_count+1,
            last_played_at=(SELECT started_at FROM playback_history WHERE id=?)
            WHERE path=(SELECT track_path FROM playback_history WHERE id=?)""", (session_id, session_id))

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
        def fold(value: str) -> str:
            decomposed = unicodedata.normalize("NFKD", str(value).casefold())
            return " ".join("".join(char for char in decomposed if not unicodedata.combining(char)).split())

        query = fold(text)
        if not query:
            return tracks
        tokens = query.split()

        def searchable(track: Track) -> str:
            return fold(" ".join((track.title, track.artist, track.album_artist, track.album, track.genre)))

        direct = [track for track in tracks if all(token in searchable(track) for token in tokens)]
        if direct:
            return direct

        def score(track: Track) -> tuple[int, str, str]:
            best = max((_similarity(query, fold(item)) for item in (track.title, track.artist, track.album)), default=0)
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
