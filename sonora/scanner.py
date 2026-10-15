from __future__ import annotations

import hashlib
import mimetypes
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from mutagen import File as MutagenFile
from mutagen.id3 import ID3
from mutagen.mp4 import MP4

from sonora.database import LibraryDatabase

SUPPORTED = {".mp3", ".m4a"}
ART_NAMES = {"cover", "folder", "front", "album", "artwork"}


class ScanCancelled(Exception):
    pass


def _first(tags, *keys) -> str:
    if not tags:
        return ""
    for key in keys:
        value = tags.get(key)
        if value:
            if isinstance(value, (list, tuple)):
                value = value[0]
            return str(value).strip()
    return ""


def _number(text: str) -> int:
    try:
        return int(text.split("/", 1)[0].strip())
    except (ValueError, AttributeError):
        return 0


def _artwork_bytes(path: Path) -> tuple[bytes, str] | None:
    try:
        raw = MutagenFile(path)
        if isinstance(raw, MP4):
            pictures = raw.tags.get("covr", []) if raw.tags else []
            if pictures:
                picture = pictures[0]
                mime = "image/png" if getattr(picture, "imageformat", None) == 14 else "image/jpeg"
                return bytes(picture), mime
        if path.suffix.lower() == ".mp3":
            tags = ID3(path)
            pictures = tags.getall("APIC")
            if pictures:
                picture = pictures[0]
                return picture.data, picture.mime or "image/jpeg"
    except Exception:
        pass

    try:
        candidates = [item for item in path.parent.iterdir() if item.is_file() and item.stem.casefold() in ART_NAMES
                      and item.suffix.casefold() in {".jpg", ".jpeg", ".png", ".webp"}]
    except OSError:
        return None
    if candidates:
        candidate = sorted(candidates, key=lambda item: (item.stem.casefold() not in {"cover", "folder", "front"}, item.name.casefold()))[0]
        mime = mimetypes.guess_type(candidate.name)[0] or "image/jpeg"
        try:
            return candidate.read_bytes(), mime
        except OSError:
            return None
    return None


def _write_artwork(path: Path, payload: bytes, mime: str, cache_dir: Path) -> str:
    extension = mimetypes.guess_extension(mime) or ".jpg"
    if extension == ".jpe":
        extension = ".jpg"
    digest = hashlib.sha256(payload).hexdigest()
    destination = cache_dir / f"{digest}{extension}"
    if not destination.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
    return str(destination)


def _accent(image_path: str) -> str:
    if not image_path:
        return ""
    try:
        import gi
        gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import GdkPixbuf

        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(image_path, 12, 12, True)
        pixels = pixbuf.get_pixels()
        channels = pixbuf.get_n_channels()
        stride = pixbuf.get_rowstride()
        samples = []
        for y in range(pixbuf.get_height()):
            for x in range(pixbuf.get_width()):
                offset = y * stride + x * channels
                samples.append((pixels[offset], pixels[offset + 1], pixels[offset + 2]))
        if not samples:
            return ""
        r = sum(sample[0] for sample in samples) // len(samples)
        g = sum(sample[1] for sample in samples) // len(samples)
        b = sum(sample[2] for sample in samples) // len(samples)
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return ""


class FolderScanner:
    def __init__(self, database: LibraryDatabase, cache_dir: Path | None = None):
        self.database = database
        self.cache_dir = cache_dir or Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "Sonora" / "Sonora" / "artwork"
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def cancel(self) -> None:
        self._cancel.set()

    def start(self, folder: str, on_progress: Callable[[int, int], None], on_finished: Callable[[int, str | None], None]) -> bool:
        if self.running:
            return False
        self._cancel.clear()

        def worker():
            count, error = self._scan(folder, on_progress)
            self._thread = None
            on_finished(count, error)

        self._thread = threading.Thread(target=worker, daemon=True, name="sonora-scanner")
        self._thread.start()
        return True

    def _scan(self, folder: str, on_progress) -> tuple[int, str | None]:
        root = str(Path(folder).expanduser().resolve())
        paths: list[Path] = []
        conn = None
        try:
            for directory, _, filenames in os.walk(root):
                if self._cancel.is_set():
                    raise ScanCancelled()
                paths.extend(Path(directory) / name for name in filenames if Path(name).suffix.casefold() in SUPPORTED)
            conn = self.database.connect()
            indexed = 0
            failures = 0
            seen: list[str] = []
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            last_progress = 0.0
            for current, path in enumerate(paths, 1):
                if self._cancel.is_set():
                    raise ScanCancelled()
                try:
                    stat = path.stat()
                    audio = MutagenFile(path, easy=True)
                    if audio is None:
                        on_progress(current, len(paths))
                        continue
                    tags = audio.tags or {}
                    title = _first(tags, "title") or path.stem
                    artist = _first(tags, "artist")
                    album_artist = _first(tags, "albumartist", "album artist")
                    album = _first(tags, "album")
                    genre = _first(tags, "genre")
                    track_no = _number(_first(tags, "tracknumber"))
                    disc_no = _number(_first(tags, "discnumber"))
                    year = _number(_first(tags, "date", "year"))
                    duration = int(float(audio.info.length) * 1000) if audio.info and audio.info.length else 0
                    artwork_path = ""
                    artwork_accent = ""
                    artwork = _artwork_bytes(path)
                    if artwork:
                        artwork_path = _write_artwork(path, artwork[0], artwork[1], self.cache_dir)
                        artwork_accent = _accent(artwork_path)
                    file_path = str(path.resolve())
                    seen.append(file_path)
                    conn.execute("""INSERT INTO tracks(
                        path, source_root, title, artist, album_artist, album, genre, composer,
                        track_number, disc_number, year, duration_ms, size_bytes, modified_ms,
                        last_scanned_at, artwork_path, artwork_accent
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(path) DO UPDATE SET source_root=excluded.source_root,
                        title=excluded.title, artist=excluded.artist, album_artist=excluded.album_artist,
                        album=excluded.album, genre=excluded.genre, track_number=excluded.track_number,
                        disc_number=excluded.disc_number, year=excluded.year, duration_ms=excluded.duration_ms,
                        size_bytes=excluded.size_bytes, modified_ms=excluded.modified_ms,
                        last_scanned_at=excluded.last_scanned_at, artwork_path=excluded.artwork_path,
                        artwork_accent=excluded.artwork_accent""",
                        (file_path, root, title, artist, album_artist, album, genre, track_no, disc_no,
                         year, duration, stat.st_size, int(stat.st_mtime * 1000), now, artwork_path, artwork_accent))
                    indexed += 1
                except Exception:
                    failures += 1
                current_time = time.monotonic()
                if current == len(paths) or current_time - last_progress >= 0.1:
                    on_progress(current, len(paths))
                    last_progress = current_time
            if seen:
                placeholders = ",".join("?" for _ in seen)
                conn.execute(f"DELETE FROM tracks WHERE source_root=? AND path NOT IN ({placeholders})", (root, *seen))
            else:
                conn.execute("DELETE FROM tracks WHERE source_root=?", (root,))
            conn.execute("UPDATE library_folders SET last_scanned_at=datetime('now') WHERE path=?", (root,))
            conn.commit()
            error = f"Skipped {failures} unreadable audio file(s)." if failures else None
            return indexed, error if not self._cancel.is_set() else "Scan cancelled"
        except ScanCancelled:
            return 0, "Scan cancelled"
        except Exception as error:
            return 0, str(error)
        finally:
            if conn is not None:
                conn.close()
