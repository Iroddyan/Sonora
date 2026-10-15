from __future__ import annotations

import threading
from pathlib import Path

import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib

from sonora.database import LibraryDatabase
from sonora.models import Track
from sonora.scanner import FolderScanner


class LibraryService:
    def __init__(self, on_changed=None, on_progress=None):
        self.database = LibraryDatabase()
        self.scanner = FolderScanner(self.database)
        self._on_changed = on_changed or (lambda: None)
        self._on_progress = on_progress or (lambda _current, _total: None)
        self.tracks: list[Track] = self.database.tracks()
        self.folders: list[str] = self.database.folders()
        self.status = ""
        self.error = ""
        self.scan_progress = (0, 0)
        self._scan_folders: list[str] = []
        self._scan_lock = threading.Lock()

    @property
    def scanning(self) -> bool:
        return self.scanner.running or bool(self._scan_folders)

    def refresh(self) -> None:
        self.tracks = self.database.tracks()
        self.folders = self.database.folders()
        self._on_changed()

    def add_folder(self, path: str) -> bool:
        if not self.database.add_folder(path):
            self.error = "That folder is already indexed or overlaps an indexed folder."
            self._on_changed()
            return False
        self.folders = self.database.folders()
        self.error = ""
        self._on_changed()
        self._scan_folders.append(str(Path(path).resolve()))
        if len(self._scan_folders) == 1:
            self._start_next_folder()
        return True

    def scan_all(self) -> None:
        if self.scanning:
            return
        self._scan_folders = list(self.folders)
        self.error = ""
        self._start_next_folder()

    def _start_next_folder(self) -> None:
        if not self._scan_folders:
            self.status = "Library is up to date."
            self.refresh()
            return
        folder = self._scan_folders[0]
        self.status = f"Scanning {folder}…"
        self._on_changed()

        def progress(current, total):
            GLib.idle_add(self._update_progress, current, total)

        def complete(count, error):
            GLib.idle_add(self._folder_complete, folder, count, error)

        if not self.scanner.start(folder, progress, complete):
            self.error = "A scan is already running."
            self._scan_folders.clear()
            self._on_changed()

    def _update_progress(self, current: int, total: int) -> bool:
        self.scan_progress = (current, total)
        if total:
            self.status = f"Scanning files: {current} of {total}"
        self._on_progress(current, total)
        return GLib.SOURCE_REMOVE

    def _folder_complete(self, folder: str, count: int, error: str | None) -> bool:
        if self._scan_folders and self._scan_folders[0] == folder:
            self._scan_folders.pop(0)
        if error and error != "Scan cancelled":
            self.error = error
        elif error == "Scan cancelled":
            self.status = "Scan cancelled."
            self._scan_folders.clear()
        else:
            self.status = f"Indexed {count} audio files in {Path(folder).name}."
        self.refresh()
        if self._scan_folders:
            GLib.timeout_add(50, self._start_next_folder)
        return GLib.SOURCE_REMOVE

    def cancel_scan(self) -> None:
        if self.scanning:
            self.scanner.cancel()

    def remove_folder(self, path: str) -> None:
        self.database.remove_folder(path)
        self.status = "Folder removed from Sonora's index. Music files were left in place."
        self.refresh()

    def search(self, query: str) -> list[Track]:
        return self.database.search(query)
