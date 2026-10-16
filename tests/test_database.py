import tempfile
import unittest
from pathlib import Path

from sonora.database import LibraryDatabase
from sonora.models import Track


class LibraryDatabaseTests(unittest.TestCase):
    def test_application_settings_are_read_with_defaults_and_upserted(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = LibraryDatabase(Path(temporary) / "library.sqlite")
            self.assertEqual(database.setting("playback_state", ""), "")
            database.set_setting("playback_state", '{"volume":0.4}')
            self.assertEqual(database.setting("playback_state"), '{"volume":0.4}')
            database.set_setting("playback_state", '{"volume":0.7}')
            self.assertEqual(database.setting("playback_state"), '{"volume":0.7}')

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
                self.assertEqual(migrated.execute("PRAGMA user_version").fetchone()[0], 6)
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
                self.assertEqual(migrated.execute("PRAGMA user_version").fetchone()[0], 6)

    def test_v5_upgrade_schedules_existing_artwork_for_thumbnail_reindex(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "library.sqlite"
            database = LibraryDatabase(path)
            with database.connect() as connection:
                connection.execute("""INSERT INTO tracks(path, source_root, title, size_bytes,
                    last_scanned_at) VALUES('/music/a.mp3', '/music', 'A', 123, '2026-01-01')""")
                connection.execute("PRAGMA user_version=5")
            upgraded = LibraryDatabase(path)
            self.assertTrue(upgraded.needs_reindex())
            self.assertEqual(upgraded.tracks()[0].size_bytes, -1)

    def test_rebuild_index_marks_tracks_for_a_real_rescan(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = LibraryDatabase(Path(temporary) / "library.sqlite")
            with database.connect() as connection:
                connection.execute("""INSERT INTO tracks(path, source_root, title, size_bytes,
                    last_scanned_at) VALUES('/music/a.mp3', '/music', 'A', 123, '2026-01-01')""")
            self.assertFalse(database.needs_reindex())
            database.mark_for_reindex()
            self.assertTrue(database.needs_reindex())
            self.assertEqual(database.tracks()[0].size_bytes, -1)

    def test_playback_history_records_real_listen_time_and_qualifies_completed_sessions(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = LibraryDatabase(Path(temporary) / "db.sqlite")
            long_track = Track(1, "/music/long.mp3", "Long", "Artist", "Artist", "Album", "",
                               1, 1, 2026, 120_000, "", "")
            short_track = Track(2, "/music/short.mp3", "Short", "Artist", "Artist", "Album", "",
                                2, 1, 2026, 4_000, "", "")

            long_session = database.start_playback(long_track, "2026-10-15T10:00:00Z")
            database.add_listened_time(long_session, 59_500)
            database.finish_playback(long_session, "completed", 500)
            short_session = database.start_playback(short_track, "2026-10-15T10:01:00Z")
            database.finish_playback(short_session, "stopped", 2_000)
            skipped_session = database.start_playback(long_track, "2026-10-15T10:02:00Z")
            database.finish_playback(skipped_session, "track_changed", 5_000)

            history = database.playback_history()
            self.assertEqual([row["listened_ms"] for row in history], [5_000, 2_000, 60_000])
            self.assertEqual([row["qualified"] for row in history], [0, 1, 1])
            self.assertEqual(len(database.playback_history(qualified_only=True)), 2)

    def test_play_count_updates_once_when_half_track_threshold_is_reached(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = LibraryDatabase(Path(temporary) / "db.sqlite")
            with database.connect() as connection:
                connection.execute("""INSERT INTO tracks(path, source_root, title, artist, album, duration_ms,
                    last_scanned_at) VALUES('/music/threshold.mp3', '/music', 'Threshold', 'Artist', 'Album',
                    120000, '2026-01-01')""")
                track_id = connection.execute("SELECT id FROM tracks").fetchone()[0]
            track = Track(track_id, "/music/threshold.mp3", "Threshold", "Artist", "Artist", "Album", "",
                          1, 1, 2026, 120_000, "", "")
            session = database.start_playback(track, "2026-10-15T10:00:00Z")
            self.assertFalse(database.add_listened_time(session, 59_000))
            self.assertEqual(database.tracks()[0].play_count, 0)
            self.assertTrue(database.add_listened_time(session, 1_000))
            self.assertEqual(database.tracks()[0].play_count, 1)
            self.assertFalse(database.finish_playback(session, "stopped", 1_000))
            self.assertEqual(database.tracks()[0].play_count, 1)

    def test_recently_played_orders_distinct_tracks_by_real_listen_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = LibraryDatabase(Path(temporary) / "db.sqlite")
            first = Track(1, "/music/first.mp3", "First", "Artist", "Artist", "Album", "",
                          1, 1, 2026, 120_000, "", "")
            second = Track(2, "/music/second.mp3", "Second", "Artist", "Artist", "Album", "",
                           2, 1, 2026, 120_000, "", "")
            untouched = Track(3, "/music/untouched.mp3", "Untouched", "Artist", "Artist", "Album", "",
                              3, 1, 2026, 120_000, "", "")

            first_session = database.start_playback(first, "2026-10-15T10:00:00Z")
            database.add_listened_time(first_session, 8_000)
            database.finish_playback(first_session, "stopped")
            repeat_session = database.start_playback(first, "2026-10-15T10:01:00Z")
            database.add_listened_time(repeat_session, 3_000)
            database.finish_playback(repeat_session, "stopped")
            second_session = database.start_playback(second, "2026-10-15T10:02:00Z")
            database.add_listened_time(second_session, 5_000)
            database.finish_playback(second_session, "stopped")
            untouched_session = database.start_playback(untouched, "2026-10-15T10:03:00Z")
            database.finish_playback(untouched_session, "stopped")

            self.assertEqual(database.recently_played_paths(), [second.path, first.path])

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

    def test_search_ignores_diacritics(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = LibraryDatabase(Path(temporary) / "db.sqlite")
            with database.connect() as connection:
                connection.execute("""INSERT INTO tracks(path, source_root, title, artist, album, last_scanned_at)
                    VALUES('/music/beyonce.mp3', '/music', 'Déjà Vu', 'Beyoncé', 'B’Day', '2026-01-01')""")
            results = database.search("deja beyonce")
            self.assertEqual([track.title for track in results], ["Déjà Vu"])

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

    def test_suggested_overrides_keep_a_reversible_before_value(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = LibraryDatabase(Path(temporary) / "db.sqlite")
            with database.connect() as connection:
                connection.execute("""INSERT INTO tracks(path, source_root, title, artist, album,
                    last_scanned_at) VALUES('/music/a.mp3', '/music', 'Artist - Song', '', '', '2026-01-01')""")
                track_id = connection.execute("SELECT id FROM tracks").fetchone()[0]
            database.set_suggested_override(track_id, "title", "Song", "Artist - Song")
            database.set_suggested_override(track_id, "artist", "Artist", "")
            self.assertEqual(database.override_records(track_id)["title"]["before_value"], "Artist - Song")
            self.assertTrue(database.override_records(track_id)["artist"]["has_before_value"])
            self.assertTrue(database.revert_override(track_id, "artist"))
            with database.connect() as connection:
                restored = connection.execute("SELECT artist FROM tracks WHERE id=?", (track_id,)).fetchone()[0]
            self.assertEqual(restored, "")
            self.assertTrue(database.revert_override(track_id, "title"))
            self.assertEqual(database.tracks()[0].title, "Artist - Song")
            self.assertNotIn("title", database.overrides(track_id))

    def test_library_health_lists_and_can_ignore_findings(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = LibraryDatabase(Path(temporary) / "db.sqlite")
            with database.connect() as connection:
                connection.executemany("""INSERT INTO tracks(path, source_root, title, artist, album,
                    album_artist, duration_ms, last_scanned_at) VALUES (?, '/music', ?, ?, ?, ?, ?, '2026-01-01')""",
                    [('/music/video.mp3', 'Artist - Song (Official Video)', '', '', '', 120_000),
                     ('/music/copy-a.mp3', 'Same', 'Artist', 'Collection', 'Artist', 120_000),
                     ('/music/copy-b.mp3', 'Same', 'Artist', 'Collection', 'Artist', 121_000)])
                database._rebuild_entities(connection)
            issues = database.health_issues()
            kinds = {issue["kind"] for issue in issues}
            self.assertTrue({"unknown_album", "missing_cover", "missing_album_artist", "title_cleanup",
                             "missing_year", "missing_track_number", "duplicate"}.issubset(kinds))
            issue = next(item for item in issues if item["kind"] == "title_cleanup")
            database.ignore_health_issue(issue["key"])
            self.assertNotIn(issue["key"], {item["key"] for item in database.health_issues()})
            ignored = next(item for item in database.health_issues(include_ignored=True)
                           if item["key"] == issue["key"])
            self.assertTrue(ignored["ignored"])

    def test_playback_counters_favorites_and_playlist_membership_are_persisted(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = LibraryDatabase(Path(temporary) / "db.sqlite")
            with database.connect() as connection:
                connection.execute("""INSERT INTO tracks(path, source_root, title, artist, album, duration_ms,
                    last_scanned_at) VALUES('/music/a.mp3', '/music', 'A', 'Artist', 'Album', 60000, '2026-01-01')""")
                track_id = connection.execute("SELECT id FROM tracks").fetchone()[0]
            track = Track(track_id, "/music/a.mp3", "A", "Artist", "Artist", "Album", "",
                          1, 1, 2026, 60_000, "", "")
            session_id = database.start_playback(track, "2026-10-15T10:00:00Z")
            self.assertEqual(database.tracks()[0].play_count, 0)
            database.finish_playback(session_id, "completed", 30_000)
            self.assertEqual(database.tracks()[0].play_count, 1)
            self.assertEqual(database.tracks()[0].last_played_at, "2026-10-15T10:00:00Z")
            database.favorite_track(track_id)
            playlist_id = database.create_playlist("Road Trip")
            database.add_playlist_track(playlist_id, track_id)
            with database.connect() as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM favorites").fetchone()[0], 1)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM playlist_tracks").fetchone()[0], 1)

    def test_favorites_and_playlist_management_round_trip(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = LibraryDatabase(Path(temporary) / "db.sqlite")
            with database.connect() as connection:
                for number in range(1, 4):
                    connection.execute("""INSERT INTO tracks(path, source_root, title, artist, album,
                        duration_ms, last_scanned_at) VALUES (?, '/music', ?, 'Artist', 'Album', 60000, '2026-01-01')""",
                        (f"/music/{number}.mp3", str(number)))
                ids = [row[0] for row in connection.execute("SELECT id FROM tracks ORDER BY id")]
            playlist_id = database.create_playlist("Mix")
            for track_id in ids:
                database.add_playlist_track(playlist_id, track_id)
            self.assertTrue(database.move_playlist_track(playlist_id, ids[2], ids[0]))
            self.assertEqual([track.id for track in database.playlist_tracks(playlist_id)],
                             [ids[2], ids[0], ids[1]])
            database.remove_playlist_track(playlist_id, ids[0])
            database.rename_playlist(playlist_id, "Road Mix")
            self.assertEqual(database.playlists()[0]["name"], "Road Mix")
            self.assertEqual([track.id for track in database.playlist_tracks(playlist_id)], [ids[2], ids[1]])
            database.favorite_track(ids[1])
            self.assertTrue(database.is_favorite(ids[1]))
            self.assertEqual([track.id for track in database.favorites()], [ids[1]])
            database.delete_playlist(playlist_id)
            self.assertEqual(database.playlists(), [])

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
