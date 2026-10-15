import tempfile
import unittest
from pathlib import Path

from sonora.database import LibraryDatabase


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
            with database.connect() as migrated:
                self.assertEqual(migrated.execute("PRAGMA user_version").fetchone()[0], 2)

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


if __name__ == "__main__":
    unittest.main()
