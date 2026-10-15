import tempfile
import unittest
from pathlib import Path

from sonora.database import LibraryDatabase
from sonora.models import Track


class LibraryDatabaseTests(unittest.TestCase):
    def test_migrates_existing_v1_track_columns_without_losing_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "library.sqlite"
            import sqlite3
            connection = sqlite3.connect(path)
            connection.executescript("""
                CREATE TABLE library_folders(path TEXT PRIMARY KEY NOT NULL, added_at TEXT NOT NULL, last_scanned_at TEXT);
                CREATE TABLE tracks(
                    id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, source_root TEXT NOT NULL,
                    title TEXT NOT NULL, artist TEXT NOT NULL DEFAULT '', album_artist TEXT NOT NULL DEFAULT '',
                    album TEXT NOT NULL DEFAULT '', genre TEXT NOT NULL DEFAULT '', composer TEXT NOT NULL DEFAULT '',
                    track_number INTEGER NOT NULL DEFAULT 0, disc_number INTEGER NOT NULL DEFAULT 0,
                    year INTEGER NOT NULL DEFAULT 0, duration_ms INTEGER NOT NULL DEFAULT 0,
                    size_bytes INTEGER NOT NULL DEFAULT 0, modified_ms INTEGER NOT NULL DEFAULT 0,
                    last_scanned_at TEXT NOT NULL
                );
                INSERT INTO tracks(path, source_root, title, last_scanned_at) VALUES('/music/a.mp3', '/music', 'A', '2026-01-01');
            """)
            connection.commit()
            connection.close()

            database = LibraryDatabase(path)
            track = database.tracks()[0]
            self.assertEqual(track.title, "A")
            self.assertEqual(track.artwork_path, "")
            self.assertEqual(track.artwork_accent, "")
            self.assertEqual(track.first_added_at, "2026-01-01")
            with database.connect() as migrated:
                self.assertEqual(migrated.execute("PRAGMA user_version").fetchone()[0], 4)
                self.assertIsNotNone(migrated.execute("SELECT name FROM sqlite_master WHERE name='playback_history'").fetchone())

    def test_migrates_schema_v2_and_preserves_existing_artwork_and_tracks(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "library.sqlite"
            import sqlite3
            connection = sqlite3.connect(path)
            connection.executescript("""
                CREATE TABLE library_folders(path TEXT PRIMARY KEY NOT NULL, added_at TEXT NOT NULL, last_scanned_at TEXT);
                CREATE TABLE tracks(
                    id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, source_root TEXT NOT NULL,
                    title TEXT NOT NULL, artist TEXT NOT NULL DEFAULT '', album_artist TEXT NOT NULL DEFAULT '',
                    album TEXT NOT NULL DEFAULT '', genre TEXT NOT NULL DEFAULT '', composer TEXT NOT NULL DEFAULT '',
                    track_number INTEGER NOT NULL DEFAULT 0, disc_number INTEGER NOT NULL DEFAULT 0,
                    year INTEGER NOT NULL DEFAULT 0, duration_ms INTEGER NOT NULL DEFAULT 0,
                    size_bytes INTEGER NOT NULL DEFAULT 0, modified_ms INTEGER NOT NULL DEFAULT 0,
                    last_scanned_at TEXT NOT NULL, artwork_path TEXT NOT NULL DEFAULT '',
                    artwork_accent TEXT NOT NULL DEFAULT ''
                );
                INSERT INTO tracks(path, source_root, title, last_scanned_at, artwork_path, artwork_accent)
                    VALUES('/music/a.mp3', '/music', 'A', '2026-10-15T10:00:00+00:00', '/cache/a.jpg', '#abcdef');
                PRAGMA user_version=2;
            """)
            connection.commit()
            connection.close()

            database = LibraryDatabase(path)

            track = database.tracks()[0]
            self.assertEqual(track.title, "A")
            self.assertEqual(track.artwork_path, "/cache/a.jpg")
            self.assertEqual(track.artwork_accent, "#abcdef")
            self.assertEqual(track.first_added_at, "2026-10-15T10:00:00+00:00")
            with database.connect() as migrated:
                self.assertEqual(migrated.execute("PRAGMA user_version").fetchone()[0], 4)

    def test_playback_history_records_real_listen_time_and_qualifies_completed_sessions(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = LibraryDatabase(Path(temporary) / "db.sqlite")
            long_track = Track(1, "/music/long.mp3", "Long", "Artist", "Artist", "Album", "",
                               1, 1, 2026, 120_000, "", "")
            short_track = Track(2, "/music/short.mp3", "Short", "Artist", "Artist", "Album", "",
                                2, 1, 2026, 4_000, "", "")

            long_session = database.start_playback(long_track, "2026-10-15T10:00:00Z")
            database.add_listened_time(long_session, 29_500)
            database.finish_playback(long_session, "completed", 500)
            short_session = database.start_playback(short_track, "2026-10-15T10:01:00Z")
            database.finish_playback(short_session, "stopped", 2_000)
            skipped_session = database.start_playback(long_track, "2026-10-15T10:02:00Z")
            database.finish_playback(skipped_session, "track_changed", 5_000)

            history = database.playback_history()
            self.assertEqual([row["listened_ms"] for row in history], [5_000, 2_000, 30_000])
            self.assertEqual([row["qualified"] for row in history], [0, 1, 1])
            self.assertEqual(len(database.playback_history(qualified_only=True)), 2)

    def test_incomplete_playback_is_recovered_as_interrupted(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "db.sqlite"
            database = LibraryDatabase(path)
            track = Track(1, "/music/a.mp3", "A", "Artist", "Artist", "Album", "",
                          1, 1, 2026, 60_000, "", "")
            session_id = database.start_playback(track, "2026-10-15T10:00:00Z")
            database.add_listened_time(session_id, 35_000)

            LibraryDatabase(path)

            event = database.playback_history()[0]
            self.assertIsNotNone(event["ended_at"])
            self.assertEqual(event["end_reason"], "interrupted")
            self.assertEqual(event["qualified"], 1)

    def test_add_folder_rejects_duplicate_and_nested_roots(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "Music"
            nested = root / "Albums"
            nested.mkdir(parents=True)
            database = LibraryDatabase(Path(temporary) / "db.sqlite")
            self.assertTrue(database.add_folder(str(root)))
            self.assertFalse(database.add_folder(str(root)))
            self.assertFalse(database.add_folder(str(nested)))
            self.assertEqual(database.folders(), [str(root.resolve())])

    def test_fuzzy_search_returns_near_title_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = LibraryDatabase(Path(temporary) / "db.sqlite")
            with database.connect() as connection:
                connection.execute("""INSERT INTO tracks(path, source_root, title, artist, album, last_scanned_at)
                    VALUES('/music/nacre.mp3', '/music', 'Nacre', 'Ethel Cain', 'Willoughby Tucker', '2026-01-01')""")
            results = database.search("Nacree")
            self.assertEqual([track.title for track in results], ["Nacre"])

    def test_migration_seeds_first_seen_from_existing_file_mtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "library.sqlite"
            import sqlite3
            connection = sqlite3.connect(path)
            connection.executescript("""
                CREATE TABLE library_folders(path TEXT PRIMARY KEY NOT NULL, added_at TEXT NOT NULL, last_scanned_at TEXT);
                CREATE TABLE tracks(
                    id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, source_root TEXT NOT NULL,
                    title TEXT NOT NULL, artist TEXT NOT NULL DEFAULT '', album_artist TEXT NOT NULL DEFAULT '',
                    album TEXT NOT NULL DEFAULT '', genre TEXT NOT NULL DEFAULT '', composer TEXT NOT NULL DEFAULT '',
                    track_number INTEGER NOT NULL DEFAULT 0, disc_number INTEGER NOT NULL DEFAULT 0,
                    year INTEGER NOT NULL DEFAULT 0, duration_ms INTEGER NOT NULL DEFAULT 0,
                    size_bytes INTEGER NOT NULL DEFAULT 0, modified_ms INTEGER NOT NULL DEFAULT 0,
                    last_scanned_at TEXT NOT NULL
                );
                INSERT INTO tracks(path, source_root, title, artist, album, size_bytes, modified_ms, last_scanned_at)
                    VALUES('/music/a.mp3', '/music', 'A', 'Akon', 'Konvicted', 42, 1760000000000, '2026-10-15');
            """)
            connection.commit()
            connection.close()

            database = LibraryDatabase(path)
            track = database.tracks()[0]
            self.assertEqual(track.size_bytes, 42)
            self.assertEqual(track.modified_ms, 1760000000000)
            self.assertTrue(track.first_seen_at.startswith("2025-10-09T08:53:20"))

    def test_artist_and_album_entities_are_normalized_and_duplicates_are_flagged(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = LibraryDatabase(Path(temporary) / "db.sqlite")
            with database.connect() as connection:
                connection.executemany("""INSERT INTO tracks(path, source_root, title, artist, album_artist,
                    album, duration_ms, last_scanned_at, first_seen_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
                    ("/music/1.mp3", "/music", "Akon & SZA", "Akon feat. SZA", "Akon", "Konvicted", 200000, "2026-01-01", "2025-01-01"),
                    ("/music/2.mp3", "/music", "Akon & SZA", "akon feat. sza", "akon", "KONVICTED", 201500, "2026-01-01", "2025-01-01"),
                ])
                database._rebuild_entities(connection)

            self.assertEqual(len(database.album_groups()), 1)
            groups = dict(database.artist_groups())
            self.assertIn("Akon", groups)
            self.assertIn("SZA", groups)
            self.assertEqual(len(groups["Akon"]), 2)
            candidates = database.duplicate_candidates()
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["duration_delta_ms"], 1500)

    def test_overrides_persist_and_are_applied_to_the_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = LibraryDatabase(Path(temporary) / "db.sqlite")
            with database.connect() as connection:
                connection.execute("""INSERT INTO tracks(path, source_root, title, last_scanned_at)
                    VALUES('/music/a.mp3', '/music', 'Original', '2026-01-01')""")
                track_id = connection.execute("SELECT id FROM tracks").fetchone()[0]
            database.set_override(track_id, "title", "Corrected")
            self.assertEqual(database.tracks()[0].title, "Corrected")
            self.assertEqual(database.overrides(track_id), {"title": "Corrected"})

    def test_playback_counters_favorites_and_playlist_membership_are_persisted(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = LibraryDatabase(Path(temporary) / "db.sqlite")
            with database.connect() as connection:
                connection.execute("""INSERT INTO tracks(path, source_root, title, artist, album, duration_ms,
                    last_scanned_at) VALUES('/music/a.mp3', '/music', 'A', 'Artist', 'Album', 60000, '2026-01-01')""")
                track_id = connection.execute("SELECT id FROM tracks").fetchone()[0]
            track = Track(track_id, "/music/a.mp3", "A", "Artist", "Artist", "Album", "",
                          1, 1, 2026, 60_000, "", "")
            database.start_playback(track, "2026-10-15T10:00:00Z")
            self.assertEqual(database.tracks()[0].play_count, 1)
            self.assertEqual(database.tracks()[0].last_played_at, "2026-10-15T10:00:00Z")
            database.favorite_track(track_id)
            playlist_id = database.create_playlist("Road Trip")
            database.add_playlist_track(playlist_id, track_id)
            with database.connect() as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM favorites").fetchone()[0], 1)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM playlist_tracks").fetchone()[0], 1)

    def test_artist_exception_list_is_editable_and_remains_empty_if_cleared(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "db.sqlite"
            database = LibraryDatabase(path)
            database.set_artist_split_exceptions(["AC/DC", "Earth, Wind & Fire"])
            self.assertEqual(database.artist_split_exceptions(), ["AC/DC", "Earth, Wind & Fire"])
            database.set_artist_split_exceptions([])
            reopened = LibraryDatabase(path)
            self.assertEqual(reopened.artist_split_exceptions(), [])


if __name__ == "__main__":
    unittest.main()
