import tempfile
import threading
import unittest
from pathlib import Path

import gi
gi.require_version("GdkPixbuf", "2.0")
from mutagen.id3 import ID3, TALB, TIT2, TPE1

from sonora.database import LibraryDatabase
from sonora.scanner import FolderScanner


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
            # Valid 1x1 PNG fixture, used only to verify local artwork discovery.
            (root / "cover.png").write_bytes(bytes.fromhex(
                "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
                "0000000b49444154789c6360f8cf0000000400019f3d2d8b0000000049454e44ae426082"
            ))
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


if __name__ == "__main__":
    unittest.main()
