import tempfile
import threading
import unittest
import os
from pathlib import Path

import gi
gi.require_version("GdkPixbuf", "2.0")
from mutagen.id3 import ID3, TALB, TIT2, TPE1
from mutagen import File as MutagenFile

from sonora.database import LibraryDatabase
from sonora.scanner import FolderScanner
from sonora.tag_editor import write_tags


def create_tagged_silent_mp3(path: Path):
    tags = ID3()
    tags.add(TIT2(encoding=3, text=["Nacre"]))
    tags.add(TPE1(encoding=3, text=["Ethel Cain"]))
    tags.add(TALB(encoding=3, text=["Willoughby Tucker, I'll Always Love You"]))
    tags.save(path)
    # Short silent MPEG frames are temporary test input and never appear in the user's library.
    frame = b"\xff\xfb\x90\x64" + bytes(413)
    path.write_bytes(path.read_bytes() + frame * 20)


class ScannerTests(unittest.TestCase):
    def test_indexes_real_tags_and_uses_neighboring_cover(self):
        try:
            from gi.repository import GdkPixbuf  # noqa: F401
        except Exception:
            self.skipTest("GdkPixbuf is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "Music"
            root.mkdir()
            track_path = root / "nacre.mp3"
            create_tagged_silent_mp3(track_path)
            # A valid 1x1 PNG fixture, used only to verify local artwork discovery.
            GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 1, 1).savev(
                str(root / "cover.png"), "png", [], [])
            database = LibraryDatabase(root / "library.sqlite")
            database.add_folder(str(root))
            finished = threading.Event()
            outcome = {}
            scanner = FolderScanner(database, root / "cache")
            self.assertTrue(scanner.start(str(root), lambda *_: None,
                                          lambda count, error: (
                                              outcome.update(count=count, error=error, running=scanner.running),
                                              finished.set(),
                                          )))
            self.assertTrue(finished.wait(5), "scanner did not finish")
            tracks = database.tracks()
            self.assertEqual(outcome.get("error"), None)
            self.assertEqual(outcome.get("count"), 1)
            self.assertFalse(outcome.get("running"), "completion callback must run after scanner state is reset")
            self.assertEqual(len(tracks), 1)
            self.assertEqual(tracks[0].title, "Nacre")
            self.assertEqual(tracks[0].artist, "Ethel Cain")
            self.assertTrue(tracks[0].artwork_path)
            thumbnail = GdkPixbuf.Pixbuf.new_from_file(tracks[0].artwork_path)
            self.assertLessEqual(max(thumbnail.get_width(), thumbnail.get_height()), 256)
            first_added = tracks[0].first_added_at

            rescanned = threading.Event()
            self.assertTrue(scanner.start(str(root), lambda *_: None,
                                          lambda *_: rescanned.set()))
            self.assertTrue(rescanned.wait(5), "scanner did not finish rescan")
            self.assertEqual(database.tracks()[0].first_added_at, first_added)

    def test_file_tag_write_is_opt_in_helper_and_creates_restore_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "nacre.mp3"
            create_tagged_silent_mp3(path)
            backup = write_tags(path, {"title": "Corrected Title"})
            self.assertTrue(backup.is_file())
            self.assertTrue(backup.name.endswith(".bak"))
            updated = MutagenFile(path, easy=True)
            original = MutagenFile(backup, easy=True)
            self.assertEqual(updated["title"], ["Corrected Title"])
            self.assertEqual(original["title"], ["Nacre"])

    def test_incremental_scan_preserves_missing_tracks_and_manual_overrides(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "Music"
            root.mkdir()
            track_path = root / "nacre.mp3"
            create_tagged_silent_mp3(track_path)
            database = LibraryDatabase(root / "library.sqlite")
            database.add_folder(str(root))
            scanner = FolderScanner(database, root / "cache")

            def scan():
                done = threading.Event()
                outcome = {}
                self.assertTrue(scanner.start(str(root), lambda *_: None,
                                              lambda count, error: (outcome.update(count=count, error=error), done.set())))
                self.assertTrue(done.wait(5), "scanner did not finish")
                self.assertIsNone(outcome.get("error"))
                return outcome["count"]

            self.assertEqual(scan(), 1)
            track = database.tracks()[0]
            database.set_override(track.id, "title", "My corrected title")
            stat = track_path.stat()
            os.utime(track_path, (stat.st_atime, stat.st_mtime + 5))
            self.assertEqual(scan(), 1)
            self.assertEqual(database.tracks()[0].title, "My corrected title")

            track_path.unlink()
            scan()
            remaining = database.tracks(include_missing=True)
            self.assertEqual(len(remaining), 1)
            self.assertTrue(remaining[0].missing)

    def test_multi_value_artist_tag_creates_primary_and_featured_credits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "Music"
            root.mkdir()
            track_path = root / "nacre.mp3"
            create_tagged_silent_mp3(track_path)
            tags = ID3(track_path)
            tags.delall("TPE1")
            tags.add(TPE1(encoding=3, text=["Akon", "SZA"]))
            tags.save(track_path)
            database = LibraryDatabase(root / "library.sqlite")
            scanner = FolderScanner(database, root / "cache")
            done = threading.Event()
            self.assertTrue(scanner.start(str(root), lambda *_: None, lambda *_: done.set()))
            self.assertTrue(done.wait(5), "scanner did not finish")
            tracks = database.tracks()
            self.assertEqual(tracks[0].primary_artist, "Akon")
            self.assertEqual(tracks[0].artist, "Akon, SZA")
            self.assertEqual({name for name, _ in database.artist_groups()}, {"Akon", "SZA"})


if __name__ == "__main__":
    unittest.main()
